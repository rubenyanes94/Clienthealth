"""Convierte los indicadores en conclusiones en lenguaje sencillo para el informe PDF.

Funciones puras: reciben los mismos diccionarios que devuelven `metrics` y `case_metrics` (del
período y del anterior) y devuelven frases. Los criterios de interpretación están documentados en
docs/METRICAS.md («Interpretación en el informe»).
"""

from dataclasses import dataclass
from typing import Any, Literal

Tone = Literal["good", "warn", "bad", "neutral"]

# Criterios de interpretación (referencias habituales; el centro puede ajustarlos).
NPS_BANDS = [(70, "excelente", "good"), (30, "bueno", "good"), (0, "por mejorar", "warn")]
CSAT_BANDS = [(4.5, "excelente", "good"), (4.0, "bueno", "good"), (3.5, "aceptable", "warn")]
GOAL_TARGET = 0.90  # meta de referencia para SLA y meta cumplida
GOAL_NEAR = 0.75
ABANDON_OK = 0.05
ABANDON_HIGH = 0.10
SMALL_SAMPLE = 30  # con menos respuestas, el NPS y el CSAT se leen con cautela
MIN_BASE_FOR_PERCENT = 10  # por debajo, una variación en % no dice nada


@dataclass
class Finding:
    topic: str
    text: str
    tone: Tone


# --- Formato en español -------------------------------------------------------------------------


def number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "—"
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def percent(value: float | None) -> str:
    return "—" if value is None else f"{number(value * 100, 0)} %"


def minutes(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 1:
        return "menos de 1 min"
    if value < 60:
        return f"{number(value, 0)} min"
    hours, rest = divmod(round(value), 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


# --- Variaciones frente al período anterior -----------------------------------------------------


def change(
    current: float | None,
    previous: float | None,
    *,
    kind: Literal["ratio", "minutes", "points", "count", "score"],
    higher_is_better: bool = True,
) -> tuple[str, Tone]:
    """«5 puntos más que el período anterior» y si eso es bueno o malo."""
    if current is None or previous is None:
        return "sin dato del período anterior para comparar", "neutral"
    delta = current - previous
    small = {"ratio": 0.005, "minutes": 0.5, "points": 0.5, "count": 0, "score": 0.05}[kind]
    if abs(delta) <= small:
        return "igual que el período anterior", "neutral"
    more = delta > 0
    tone: Tone = "good" if more == higher_is_better else "bad"
    if kind == "ratio":
        amount = f"{number(abs(delta) * 100, 0)} puntos"
    elif kind == "minutes":
        amount = minutes(abs(delta))
    elif kind == "points":
        amount = f"{number(abs(delta), 0)} puntos"
    elif kind == "score":
        amount = number(abs(delta), 2).rstrip("0").rstrip(",")
    else:
        # Con una base muy chica el porcentaje engaña («14.200 % más»): se da solo la diferencia.
        pct = abs(delta) / previous * 100 if previous >= MIN_BASE_FOR_PERCENT else None
        amount = f"{number(abs(delta), 0)} ({number(pct, 0)} %)" if pct else number(abs(delta), 0)
    return f"{amount} {'más' if more else 'menos'} que el período anterior", tone


def band(value: float, bands: list[tuple[float, str, Tone]], low: str) -> tuple[str, Tone]:
    for threshold, label, tone in bands:
        if value >= threshold:
            return label, tone
    return low, "bad"


# --- Conclusiones por tema ----------------------------------------------------------------------


def nps(current: dict[str, Any], previous: dict[str, Any] | None) -> list[Finding]:
    score = current["score"]
    if score is None:
        return [Finding("NPS", "No hubo respuestas de NPS en el período.", "neutral")]
    label, tone = band(score, NPS_BANDS, "crítico")
    total = current["responses"]
    promoters = current["promoters"] / total
    detractors = current["detractors"] / total
    text = (
        f"El NPS fue {number(score)}, un nivel {label}: {percent(promoters)} de los pacientes nos "
        f"recomendaría con entusiasmo y {percent(detractors)} quedó insatisfecho."
    )
    if previous and previous["score"] is not None:
        diff, _ = change(score, previous["score"], kind="points")
        text += f" Son {diff}."
    findings = [Finding("NPS", text, tone)]
    if total < SMALL_SAMPLE:
        findings.append(
            Finding(
                "NPS",
                f"Solo {total} respuestas: el resultado puede variar mucho con pocas opiniones.",
                "warn",
            )
        )
    return findings


def csat(current: dict[str, Any], previous: dict[str, Any] | None) -> list[Finding]:
    avg = current["avg"]
    if avg is None:
        return [Finding("CSAT", "No hubo encuestas de satisfacción respondidas.", "neutral")]
    label, tone = band(avg, CSAT_BANDS, "bajo")
    text = (
        f"La satisfacción tras la atención por WhatsApp fue {number(avg, 2)} de 5 ({label}); "
        f"{percent(current['satisfied']['value'])} calificó con 4 o 5."
    )
    if previous and previous["avg"] is not None:
        diff, _ = change(avg, previous["avg"], kind="score")
        text += f" Son {diff}."
    return [Finding("CSAT", text, tone)]


def _goal_tone(value: float) -> Tone:
    return "good" if value >= GOAL_TARGET else "warn" if value >= GOAL_NEAR else "bad"


def cases(
    current: dict[str, Any], previous: dict[str, Any] | None, areas: list[dict[str, Any]]
) -> list[Finding]:
    if current["received"] == 0:
        return [Finding("Casos", "No hubo casos en el período.", "neutral")]
    findings = []
    goal = current["goal"]["value"]
    attention = current["time_to_attention"]["median"]
    if goal is not None:
        text = (
            f"El {percent(goal)} de los casos se empezó a atender dentro de la meta de "
            f"{current['goal_minutes']} minutos (mediana: {minutes(attention)})."
        )
        if previous and previous["goal"]["value"] is not None:
            diff, _ = change(goal, previous["goal"]["value"], kind="ratio")
            text += f" Son {diff}."
        findings.append(Finding("Casos", text, _goal_tone(goal)))
    volume, _ = change(current["created"], previous["created"] if previous else None, kind="count")
    findings.append(
        Finding(
            "Casos",
            f"Se crearon {number(current['created'])} casos y se cerraron "
            f"{number(current['closed'])}; {volume}.",
            "neutral",
        )
    )
    ranked = [a for a in areas if a["goal"]["value"] is not None and a["received"] >= 5]
    if len(ranked) >= 2:
        worst = min(ranked, key=lambda a: a["goal"]["value"])
        if worst["goal"]["value"] < GOAL_TARGET:
            findings.append(
                Finding(
                    "Casos",
                    f"{worst['name']} es el área con menos casos atendidos a tiempo "
                    f"({percent(worst['goal']['value'])}).",
                    _goal_tone(worst["goal"]["value"]),
                )
            )
    return findings


def whatsapp(
    current: dict[str, Any], previous: dict[str, Any] | None, hours: list[dict[str, Any]]
) -> list[Finding]:
    if current["episodes"] == 0:
        return [Finding("WhatsApp", "No hubo chats atendidos por personas.", "neutral")]
    findings = []
    sla = current["sla"]["value"]
    first = current["first_response"]["median"]
    if sla is not None:
        text = (
            f"El {percent(sla)} de los chats tuvo su primera respuesta dentro de la meta del área "
            f"(mediana: {minutes(first)})."
        )
        if previous and previous["sla"]["value"] is not None:
            diff, _ = change(sla, previous["sla"]["value"], kind="ratio")
            text += f" Son {diff}."
        findings.append(Finding("WhatsApp", text, _goal_tone(sla)))
    abandon = current["abandon_rate"]["value"]
    if abandon is not None:
        tone: Tone = (
            "good" if abandon <= ABANDON_OK else "warn" if abandon <= ABANDON_HIGH else "bad"
        )
        findings.append(
            Finding(
                "WhatsApp",
                f"{percent(abandon)} de los pacientes que pidieron hablar con una persona nunca "
                "recibió respuesta.",
                tone,
            )
        )
    busiest = max(hours, key=lambda h: h["inbound_messages"], default=None)
    if busiest and busiest["inbound_messages"]:
        findings.append(
            Finding(
                "WhatsApp",
                f"La hora con más mensajes fue de {busiest['hour']}:00 a {busiest['hour']}:59 "
                f"({number(busiest['inbound_messages'])} mensajes): conviene reforzar el personal "
                "en ese horario.",
                "neutral",
            )
        )
    return findings


def highlights(sections: list[list[Finding]], limit: int = 6) -> list[Finding]:
    """Lo más importante primero: problemas, luego logros, luego el resto."""
    order = {"bad": 0, "warn": 1, "good": 2, "neutral": 3}
    flat = [f for section in sections for f in section]
    return sorted(flat, key=lambda f: order[f.tone])[:limit]
