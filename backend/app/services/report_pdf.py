"""Informe de indicadores en PDF: resumen, conclusiones y gráficas sencillas.

Se arma en el servidor con ReportLab (sin dependencias del sistema). Solo usa datos agregados:
ningún nombre, teléfono ni texto de pacientes.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Area, ContactReason
from app.services import case_metrics, metrics
from app.services import report_analysis as an

INK = colors.HexColor("#0b0b0d")
INK2 = colors.HexColor("#3f3f46")
INK3 = colors.HexColor("#71717a")
LINE = colors.HexColor("#e4e4e7")
SOFT = colors.HexColor("#f4f4f5")
BLUE = colors.HexColor("#2a78d6")  # la serie de las gráficas, la misma de los Paneles
TONE = {
    "good": colors.HexColor("#15803d"),
    "warn": colors.HexColor("#b45309"),
    "bad": colors.HexColor("#dc2626"),
    "neutral": INK3,
}
PASSIVE = colors.HexColor("#a1a1aa")
MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
WIDTH = PAGE_W - 2 * MARGIN


# --- Datos --------------------------------------------------------------------------------------


@dataclass
class ReportData:
    date_from: date
    date_to: date
    previous_from: date
    previous_to: date
    area_name: str | None
    generated_by: str
    generated_at: datetime
    wa: dict[str, Any]
    wa_previous: dict[str, Any]
    wa_hours: list[dict[str, Any]]
    csat_daily: list[dict[str, Any]]
    cases: dict[str, Any]
    cases_previous: dict[str, Any]
    case_areas: list[dict[str, Any]]
    case_reasons: list[dict[str, Any]]


def previous_period(date_from: date, date_to: date) -> tuple[date, date]:
    """El período anterior de la misma duración, justo antes."""
    days = (date_to - date_from).days + 1
    return date_from - timedelta(days=days), date_from - timedelta(days=1)


def collect(
    db: Session,
    date_from: date,
    date_to: date,
    area_id: int | None,
    generated_by: str,
    now: datetime,
) -> ReportData:
    prev_from, prev_to = previous_period(date_from, date_to)
    wa = metrics.load_period(db, date_from, date_to, area_id, now)
    wa_prev = metrics.load_period(db, prev_from, prev_to, area_id, now)
    cases = case_metrics.load_period(db, date_from, date_to, area_id, now)
    cases_prev = case_metrics.load_period(db, prev_from, prev_to, area_id, now)
    areas = {a.id: a.name for a in db.scalars(select(Area))}
    reasons = {r.id: r.name for r in db.scalars(select(ContactReason))}
    return ReportData(
        date_from=date_from,
        date_to=date_to,
        previous_from=prev_from,
        previous_to=prev_to,
        area_name=areas.get(area_id) if area_id else None,
        generated_by=generated_by,
        generated_at=now,
        wa=metrics.overview(wa),
        wa_previous=metrics.overview(wa_prev),
        wa_hours=metrics.by_hour(wa),
        csat_daily=metrics.csat_daily(wa),
        cases=case_metrics.overview(cases),
        cases_previous=case_metrics.overview(cases_prev),
        case_areas=case_metrics.by_area(cases, areas),
        case_reasons=case_metrics.reasons(cases, reasons),
    )


# --- Textos -------------------------------------------------------------------------------------


def period_label(start: date, end: date) -> str:
    """«1 al 30 de noviembre de 2026», «28 de octubre al 3 de noviembre de 2026»."""
    if start == end:
        return f"{start.day} de {MONTHS[start.month - 1]} de {start.year}"
    if start.year != end.year:
        return (
            f"{start.day} de {MONTHS[start.month - 1]} de {start.year} al "
            f"{end.day} de {MONTHS[end.month - 1]} de {end.year}"
        )
    if start.month != end.month:
        return (
            f"{start.day} de {MONTHS[start.month - 1]} al "
            f"{end.day} de {MONTHS[end.month - 1]} de {end.year}"
        )
    return f"{start.day} al {end.day} de {MONTHS[start.month - 1]} de {start.year}"


STYLE = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK),
    "h2": ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=6
    ),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=INK),
    "body": ParagraphStyle(
        "body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK2
    ),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=11, textColor=INK3),
    "label": ParagraphStyle("label", fontName="Helvetica", fontSize=8, leading=10, textColor=INK3),
    "value": ParagraphStyle(
        "value", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=INK
    ),
}


def _p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLE[style])


# --- Piezas -------------------------------------------------------------------------------------


def kpi(label: str, value: str, delta: tuple[str, an.Tone]) -> list[Paragraph]:
    note, tone = delta
    color = TONE[tone].hexval()[2:]
    return [
        _p(escape(label), "label"),
        _p(escape(value), "value"),
        Paragraph(
            f'<font color="#{color}">{escape(note)}</font>',
            ParagraphStyle("delta", parent=STYLE["small"]),
        ),
    ]


def kpi_grid(cells: list[list[Paragraph]], columns: int = 4) -> Table:
    rows = [cells[i : i + columns] for i in range(0, len(cells), columns)]
    table = Table(rows, colWidths=[WIDTH / columns] * columns)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("LINEBELOW", (0, 0), (-1, -2), 6, colors.white),
                ("LINEAFTER", (0, 0), (-2, -1), 6, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def findings_list(findings: list[an.Finding]) -> Table:
    rows = []
    for finding in findings:
        dot = Drawing(8, 8)
        dot.add(Rect(0, 1, 6, 6, fillColor=TONE[finding.tone], strokeColor=None))
        rows.append([dot, _p(escape(finding.text))])
    table = Table(rows, colWidths=[5 * mm, WIDTH - 5 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (0, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def nps_bar(nps: dict[str, Any]) -> Drawing:
    """Barra apilada: detractores, pasivos y promotores, con su porcentaje escrito."""
    drawing = Drawing(WIDTH, 46)
    total = nps["responses"]
    parts = [
        ("Detractores (0-6)", nps["detractors"], TONE["bad"]),
        ("Pasivos (7-8)", nps["passives"], PASSIVE),
        ("Promotores (9-10)", nps["promoters"], TONE["good"]),
    ]
    x = 0.0
    for _label, count, color in parts:
        width = WIDTH * count / total if total else 0
        if width:
            drawing.add(Rect(x, 22, width - 1.5, 18, fillColor=color, strokeColor=None))
            if width > 34:
                drawing.add(
                    String(x + 5, 27.5, an.percent(count / total), fontName="Helvetica-Bold",
                           fontSize=8.5, fillColor=colors.white)
                )  # fmt: skip
        x += width
    legend_x = 0.0
    for label, count, color in parts:
        drawing.add(Rect(legend_x, 6, 7, 7, fillColor=color, strokeColor=None))
        drawing.add(
            String(legend_x + 10, 6.5, f"{label}: {count}", fontName="Helvetica", fontSize=8,
                   fillColor=INK2)
        )  # fmt: skip
        legend_x += WIDTH / 3
    return drawing


def horizontal_bars(
    rows: list[tuple[str, float]], *, value_format, max_value: float | None = None, target=None
) -> Drawing:
    """Barras horizontales con la cifra al final. `target` dibuja una línea de referencia."""
    height = 16 * len(rows) + 22
    drawing = Drawing(WIDTH, height)
    chart = HorizontalBarChart()
    chart.x, chart.y = 120, 14
    chart.width, chart.height = WIDTH - 170, height - 22
    chart.data = [[v for _, v in reversed(rows)]]
    chart.categoryAxis.categoryNames = [label[:26] for label, _ in reversed(rows)]
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = INK2
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.strokeColor = LINE
    chart.categoryAxis.tickLeft = 0
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max_value or (max(v for _, v in rows) * 1.15 or 1)
    chart.valueAxis.visible = False
    chart.bars[0].fillColor = BLUE
    chart.bars[0].strokeColor = None
    chart.barWidth = 9
    chart.barSpacing = 4
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fontSize = 8
    chart.barLabels.fillColor = INK
    chart.barLabels.nudge = 14
    chart.barLabelFormat = value_format
    if target is not None:  # detrás de las barras, para no tapar las cifras
        x = chart.x + chart.width * target / chart.valueAxis.valueMax
        drawing.add(Line(x, chart.y - 4, x, chart.y + chart.height, strokeColor=INK3,
                         strokeDashArray=[2, 2], strokeWidth=0.8))  # fmt: skip
        drawing.add(String(x + 3, 2, f"meta {an.percent(target)}", fontName="Helvetica",
                           fontSize=7, fillColor=INK3))  # fmt: skip
    drawing.add(chart)
    return drawing


def hours_chart(hours: list[dict[str, Any]]) -> Drawing:
    drawing = Drawing(WIDTH, 128)
    chart = VerticalBarChart()
    chart.x, chart.y = 24, 28
    chart.width, chart.height = WIDTH - 30, 92
    chart.data = [[h["inbound_messages"] for h in hours]]
    chart.categoryAxis.categoryNames = [str(h["hour"]) if h["hour"] % 2 == 0 else "" for h in hours]
    for axis in (chart.categoryAxis, chart.valueAxis):
        axis.labels.fontName = "Helvetica"
        axis.labels.fontSize = 7
        axis.labels.fillColor = INK3
        axis.strokeColor = LINE
    chart.valueAxis.valueMin = 0
    chart.valueAxis.gridStrokeColor = LINE
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.visibleAxis = False
    chart.bars[0].fillColor = BLUE
    chart.bars[0].strokeColor = None
    chart.groupSpacing = 3
    drawing.add(chart)
    drawing.add(String(chart.x, 2, "Hora del día (hora de Caracas)", fontName="Helvetica",
                       fontSize=7, fillColor=INK3))  # fmt: skip
    return drawing


def csat_chart(days: list[dict[str, Any]]) -> Drawing | None:
    points = [(i, d["avg"]) for i, d in enumerate(days) if d["avg"] is not None]
    if len(points) < 2:
        return None
    drawing = Drawing(WIDTH, 110)
    chart = LinePlot()
    chart.x, chart.y = 24, 20
    chart.width, chart.height = WIDTH - 34, 82
    chart.data = [points]
    chart.lines[0].strokeColor = BLUE
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = None
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = max(len(days) - 1, 1)
    step = max(1, len(days) // 7)
    chart.xValueAxis.valueSteps = list(range(0, len(days), step))
    chart.xValueAxis.labelTextFormat = lambda i: (
        f"{days[int(i)]['day'].day} {MONTHS[days[int(i)]['day'].month - 1][:3]}"
        if 0 <= int(i) < len(days)
        else ""
    )
    chart.yValueAxis.valueMin = 1
    chart.yValueAxis.valueMax = 5
    chart.yValueAxis.valueSteps = [1, 2, 3, 4, 5]
    chart.yValueAxis.gridStrokeColor = LINE
    chart.yValueAxis.visibleGrid = True
    chart.yValueAxis.visibleAxis = False
    for axis in (chart.xValueAxis, chart.yValueAxis):
        axis.labels.fontName = "Helvetica"
        axis.labels.fontSize = 7
        axis.labels.fillColor = INK3
        axis.strokeColor = LINE
    drawing.add(chart)
    for x, y in points:  # un punto por día con respuestas: días sin datos no tienen línea
        px = chart.x + chart.width * x / chart.xValueAxis.valueMax
        py = chart.y + chart.height * (y - 1) / 4
        drawing.add(Rect(px - 2, py - 2, 4, 4, fillColor=BLUE, strokeColor=colors.white))
    return drawing


def data_table(header: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    table = Table([header, *rows], colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica", 7.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK3),
                ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK2),
                ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 8.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
                ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


# --- Documento ----------------------------------------------------------------------------------


def _frame_page(data: ReportData):
    title = "Informe de atención al paciente"
    scope = data.area_name or "Todas las áreas"
    tz = ZoneInfo(get_settings().timezone)
    stamp = data.generated_at.astimezone(tz)

    def draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0, PAGE_H - 22 * mm, PAGE_W, 22 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(MARGIN, PAGE_H - 12 * mm, title)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(
            MARGIN, PAGE_H - 17 * mm, f"{period_label(data.date_from, data.date_to)} · {scope}"
        )
        canvas.setFillColor(INK3)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(
            MARGIN,
            10 * mm,
            f"Generado el {stamp.day} de {MONTHS[stamp.month - 1]} de {stamp.year}, "
            f"{stamp:%H:%M}, por {data.generated_by}. Tiempos en minutos hábiles.",
        )
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    return draw


def build(data: ReportData) -> bytes:
    wa, wa_prev = data.wa, data.wa_previous
    cs, cs_prev = data.cases, data.cases_previous

    sections = {
        "nps": an.nps(wa["nps"], wa_prev["nps"]),
        "csat": an.csat(wa["csat"], wa_prev["csat"]),
        "cases": an.cases(cs, cs_prev, data.case_areas),
        "wa": an.whatsapp(wa, wa_prev, data.wa_hours),
    }
    story: list = []

    # 1. Resumen
    story += [
        _p("Resumen del período", "h1"),
        Spacer(0, 2),
        _p(
            f"Comparado con el período anterior equivalente: "
            f"{period_label(data.previous_from, data.previous_to)}.",
            "small",
        ),
        Spacer(0, 10),
        kpi_grid(
            [
                kpi(
                    "NPS (recomendación)",
                    an.number(wa["nps"]["score"]),
                    an.change(wa["nps"]["score"], wa_prev["nps"]["score"], kind="points"),
                ),
                kpi(
                    "CSAT (satisfacción)",
                    f"{an.number(wa['csat']['avg'], 2)} / 5" if wa["csat"]["avg"] else "—",
                    an.change(wa["csat"]["avg"], wa_prev["csat"]["avg"], kind="score"),
                ),
                kpi(
                    "Casos atendidos a tiempo",
                    an.percent(cs["goal"]["value"]),
                    an.change(cs["goal"]["value"], cs_prev["goal"]["value"], kind="ratio"),
                ),
                kpi(
                    "Hasta atender un caso",
                    an.minutes(cs["time_to_attention"]["median"]),
                    an.change(
                        cs["time_to_attention"]["median"],
                        cs_prev["time_to_attention"]["median"],
                        kind="minutes",
                        higher_is_better=False,
                    ),
                ),
                kpi(
                    "Chats respondidos a tiempo",
                    an.percent(wa["sla"]["value"]),
                    an.change(wa["sla"]["value"], wa_prev["sla"]["value"], kind="ratio"),
                ),
                kpi(
                    "1ª respuesta WhatsApp",
                    an.minutes(wa["first_response"]["median"]),
                    an.change(
                        wa["first_response"]["median"],
                        wa_prev["first_response"]["median"],
                        kind="minutes",
                        higher_is_better=False,
                    ),
                ),
                kpi(
                    "Casos creados",
                    an.number(cs["created"]),
                    (an.change(cs["created"], cs_prev["created"], kind="count")[0], "neutral"),
                ),
                kpi(
                    "Chats de WhatsApp",
                    an.number(wa["conversations"]),
                    (
                        an.change(wa["conversations"], wa_prev["conversations"], kind="count")[0],
                        "neutral",
                    ),
                ),
            ]
        ),
        Spacer(0, 14),
        _p("Lo más importante", "h2"),
        Spacer(0, 4),
        findings_list(an.highlights(list(sections.values()))),
        Spacer(0, 6),
        _p(
            "Verde: va bien. Ámbar: conviene vigilarlo. Rojo: requiere atención. Gris: dato "
            "informativo.",
            "small",
        ),
    ]

    # 2. Satisfacción
    nps = wa["nps"]
    nps_block = [CondPageBreak(70 * mm), Spacer(0, 14), _p("Satisfacción del paciente", "h2")]
    nps_block += [Spacer(0, 6), _p(f"NPS: {an.number(nps['score'])}", "h3"), Spacer(0, 4)]
    if nps["responses"]:
        nps_block += [nps_bar(nps), Spacer(0, 4)]
    nps_block += [findings_list(sections["nps"])]
    nps_block += [
        _p(
            "El NPS mide qué tan probable es que el paciente recomiende el centro, del 0 al 10. Se "
            "calcula restando el porcentaje de detractores (0 a 6) al de promotores (9 a 10), y va "
            "de -100 a 100. Desde 30 se considera bueno y desde 70, excelente.",
            "small",
        )
    ]
    story.append(KeepTogether(nps_block))
    csat_block = [Spacer(0, 10), _p("Satisfacción tras la atención (CSAT)", "h3"), Spacer(0, 4)]
    csat_block.append(findings_list(sections["csat"]))
    chart = csat_chart(data.csat_daily)
    if chart:
        csat_block += [_p("Promedio por día, escala de 1 a 5", "small"), chart]
    story.append(KeepTogether(csat_block))

    # 3. Casos
    story += [CondPageBreak(80 * mm), Spacer(0, 14), _p("Casos entre áreas", "h2"), Spacer(0, 4)]
    story.append(findings_list(sections["cases"]))
    areas = [a for a in data.case_areas if a["goal"]["value"] is not None]
    if areas:
        story.append(
            KeepTogether(
                [
                    Spacer(0, 6),
                    _p("Casos atendidos a tiempo, por área", "h3"),
                    horizontal_bars(
                        [(a["name"], a["goal"]["value"]) for a in areas],
                        value_format=lambda v: an.percent(v),
                        max_value=1.0,
                        target=an.GOAL_TARGET,
                    ),
                ]
            )
        )
    if data.case_areas:
        story.append(
            KeepTogether(
                [
                    Spacer(0, 8),
                    data_table(
                        [
                            "Área",
                            "Recibidos",
                            "Hasta atender",
                            "A tiempo",
                            "En atención",
                            "Cerrados",
                        ],
                        [
                            [
                                escape(a["name"]),
                                an.number(a["received"]),
                                an.minutes(a["time_to_attention"]["median"]),
                                an.percent(a["goal"]["value"]),
                                an.minutes(a["attention_time"]["median"]),
                                an.number(a["closed"]),
                            ]
                            for a in data.case_areas
                        ],
                        [WIDTH * 0.3] + [WIDTH * 0.14] * 5,
                    ),
                ]
            )
        )
    top = [r for r in data.case_reasons if r["count"]][:6]
    if top:
        story.append(
            KeepTogether(
                [
                    Spacer(0, 10),
                    _p("Motivos más frecuentes de los casos cerrados", "h3"),
                    horizontal_bars(
                        [(r["name"], r["count"]) for r in top], value_format=lambda v: an.number(v)
                    ),
                ]
            )
        )

    # 4. WhatsApp
    story += [
        CondPageBreak(90 * mm),
        Spacer(0, 14),
        _p("Atención por WhatsApp", "h2"),
        Spacer(0, 4),
    ]
    story.append(findings_list(sections["wa"]))
    if any(h["inbound_messages"] for h in data.wa_hours):
        story.append(
            KeepTogether(
                [
                    Spacer(0, 6),
                    _p("Mensajes de pacientes por hora", "h3"),
                    hours_chart(data.wa_hours),
                ]
            )
        )
    story.append(
        KeepTogether(
            [
                Spacer(0, 8),
                data_table(
                    ["Indicador", "Este período", "Período anterior"],
                    [
                        [
                            "Primera respuesta (mediana)",
                            an.minutes(wa["first_response"]["median"]),
                            an.minutes(wa_prev["first_response"]["median"]),
                        ],
                        [
                            "Respondidos a tiempo",
                            an.percent(wa["sla"]["value"]),
                            an.percent(wa_prev["sla"]["value"]),
                        ],
                        [
                            "Resolución (mediana)",
                            an.minutes(wa["resolution_time"]["median"]),
                            an.minutes(wa_prev["resolution_time"]["median"]),
                        ],
                        [
                            "Sin respuesta (abandono)",
                            an.percent(wa["abandon_rate"]["value"]),
                            an.percent(wa_prev["abandon_rate"]["value"]),
                        ],
                        [
                            "Resueltas por el bot",
                            an.percent(wa["bot_containment"]["value"]),
                            an.percent(wa_prev["bot_containment"]["value"]),
                        ],
                    ],  # fmt: skip
                    [WIDTH * 0.5, WIDTH * 0.25, WIDTH * 0.25],
                ),
            ]
        )
    )

    # 5. Glosario
    glossary = [
        ("NPS", "qué tan probable es que el paciente recomiende el centro (encuesta mensual)."),
        ("CSAT", "satisfacción con la atención recibida por WhatsApp, del 1 al 5."),
        (
            "A tiempo",
            "casos que se empezaron a atender, o chats que se respondieron, dentro de la meta.",
        ),
        ("Mediana", "el valor del medio: la mitad tardó menos y la otra mitad, más."),
        (
            "Minutos hábiles",
            "solo cuentan las horas de atención del área, sin noches, domingos ni feriados.",
        ),
    ]
    story.append(
        KeepTogether(
            [Spacer(0, 16), _p("Cómo leer este informe", "h2"), Spacer(0, 4)]
            + [_p(f"<b>{escape(k)}</b>: {escape(v)}", "small") for k, v in glossary]
        )
    )

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=30 * mm,
        bottomMargin=18 * mm,
        title="Informe de atención al paciente",
        author="Consola de Atención al Paciente",
    )
    frame = Frame(MARGIN, 18 * mm, WIDTH, PAGE_H - 48 * mm, id="cuerpo")
    doc.addPageTemplates([PageTemplate(id="pagina", frames=[frame], onPage=_frame_page(data))])
    doc.build(story)
    return buffer.getvalue()
