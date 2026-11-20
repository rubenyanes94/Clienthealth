"""Directorio de consultorios. Las fichas imitan el formato real de la web del centro, con datos
ficticios: nombres, teléfonos y correos inventados."""

import pytest

from app.models.enums import AgentRole
from app.services.directory_parser import parse_content, parse_phones, split_name
from tests.conftest import login, make_agent


def p(*lines: str) -> str:
    return "".join(f'\n<p class="wp-block-paragraph">{line}</p>\n\n' for line in lines)


FICHA_COMPLETA = p(
    "<strong>Cardiología. Cardiología intervencionista</strong>",
    "Edificio Anexo B, piso 5, consultorio 5B",
    "Lunes a Viernes",
    "8:00 a.m. 1:00 p.m .",
    "Previa cita",
    "Consultorio: :&nbsp;0212 5550001",
    "Celular: 0414 5550002",
    "doctora.prueba@example.com&nbsp;&nbsp;&nbsp;",
    "consulta.prueba@example.com",
)


# --- Intérprete ---------------------------------------------------------------------------------


def test_parses_a_complete_card():
    d = parse_content(FICHA_COMPLETA)
    assert d.specialty_text == "Cardiología. Cardiología intervencionista"
    assert [(o.building, o.floor, o.office) for o in d.offices] == [("Anexo B", "5", "5B")]
    assert d.schedule == ["Lunes a Viernes", "8:00 a.m. 1:00 p.m."]
    assert d.by_appointment is True
    assert [(x.label, x.display, x.mobile) for x in d.phones] == [
        ("Consultorio", "0212 5550001", False),
        ("Celular", "0414 5550002", True),
    ]
    assert d.emails == ["doctora.prueba@example.com", "consulta.prueba@example.com"]
    assert d.review_notes == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Edificio Anexo B, piso 3 consultorio 3C", ("Anexo B", "3", "3C")),  # sin coma
        ("Edificio Anexo A, piso 2, consultorio 275", ("Anexo A", "2", "275")),
        ("Torre Este, nivel 4, consultorio 4-12", ("Torre Este", "4", "4-12")),
        ("Edificio Anexo C, planta baja, consultorio PB-3", ("Anexo C", "PB", "PB-3")),
        ("Anexo D piso 4 consultorio Nº 4d", ("Anexo D", "4", "4D")),
    ],
)
def test_parses_the_location_however_it_is_written(text, expected):
    office = parse_content(p(text)).offices[0]
    assert (office.building, office.floor, office.office) == expected


def test_second_number_inherits_the_area_code():
    phones = parse_phones("Consultorio: 0212 5550003 &#8211; 5550004".replace("&#8211;", "–"))
    assert [x.display for x in phones] == ["0212 5550003", "0212 5550004"]


def test_mobile_labelled_as_office_is_still_a_mobile():
    [phone] = parse_phones("Consultorio: 0424 5550005")
    assert phone.mobile is True and phone.label == "Consultorio"


@pytest.mark.parametrize(
    "line",
    [
        "Martes y jueves: 4:00 p.m.",
        "Miércoles: 10:00 a.m. a 5:00 p.m.",
        "Lunes y viernes 8:00 a.m. a 12:00 m",
        "Miércoles 2:00 a 5:00 p.m.",
        "Sábados de 9:00 a.m. a 12:00 m",
    ],
)
def test_recognises_schedule_lines(line):
    assert parse_content(p(line)).schedule == [line]


def test_empty_paragraphs_and_spaces_are_ignored():
    d = parse_content(
        p("<strong>Neurología clínica</strong>", "", "&nbsp;", "Anexo B, piso 3, consultorio 3C")
    )
    assert d.raw_lines == ["Neurología clínica", "Anexo B, piso 3, consultorio 3C"]


def test_unknown_or_incomplete_data_is_kept_and_flagged():
    d = parse_content(p("<strong>Pediatría</strong>", "Piso 2", "Atiende en la sede de Chacao"))
    assert d.other_lines == ["Atiende en la sede de Chacao"]
    assert any("Ubicación incompleta" in n for n in d.review_notes)
    assert any("sin clasificar" in n for n in d.review_notes)
    missing = parse_content(p("<strong>Pediatría</strong>", "Consultorio: 0212 5550006"))
    assert missing.review_notes == ["No se encontró la ubicación del consultorio"]


def test_name_is_split_into_surnames_and_names():
    assert split_name("Prueba Ficticia,  Ana María") == (
        "Prueba Ficticia",
        "Ana María",
        "Ana María Prueba Ficticia",
    )


# --- Importación --------------------------------------------------------------------------------

CATEGORIES = [
    {"id": 31, "name": "Cardiología", "slug": "cardiologia"},
    {"id": 118, "name": "Cardiología intervencionista", "slug": "cardiologia-intervencionista"},
    {"id": 78, "name": "Neurología", "slug": "neurologia"},
    {"id": 1, "name": "Sin categoría", "slug": "sin-categoria"},
]
TAGS = [{"id": 107, "name": "A", "slug": "a"}, {"id": 108, "name": "B", "slug": "b"}]


def post(
    pid, title, content=FICHA_COMPLETA, categories=(31, 118), tags=(107,), modified="2026-01-01"
):
    return {
        "id": pid,
        "link": f"https://www.centromedicodecaracas.com/?p={pid}",
        "modified": modified,
        "title": {"rendered": title},
        "content": {"rendered": content},
        "categories": list(categories),
        "tags": list(tags),
    }


def export(*posts):
    return {"posts": list(posts), "categories": CATEGORIES, "tags": TAGS}


@pytest.fixture
def admin(db):
    make_agent(db, "admin@cm.test", AgentRole.ADMIN)
    return login("admin@cm.test")


def run(client, body, apply=False):
    return client.post("/api/directory/import", params={"apply": apply}, json=body)


def test_preview_does_not_save_and_apply_does(admin, lab_agent):
    body = export(
        post(1, "Prueba Uno, Ana"), post(2, "Prueba Dos, Luis", categories=(78, 1), tags=(108,))
    )
    preview = run(admin, body).json()
    assert preview["applied"] is False and preview["created"] == 2 and preview["total"] == 2
    assert lab_agent.get("/api/directory").json()["doctors"] == []

    applied = run(admin, body, apply=True).json()
    assert applied["applied"] is True and applied["created"] == 2
    data = lab_agent.get("/api/directory").json()
    assert [d["name"] for d in data["doctors"]] == ["Prueba Dos, Luis", "Prueba Uno, Ana"]
    luis = data["doctors"][0]
    assert luis["specialties"] == ["Neurología"]  # «Sin categoría» no cuenta
    assert luis["offices"][0]["office"] == "5B"
    assert "neurologia" in luis["search_text"] and "5b" in luis["search_text"]
    assert data["last_import"]["agent_name"] == "Admin" and data["last_import"]["total"] == 2


def test_reimport_detects_changes_and_removals(admin):
    run(admin, export(post(1, "Prueba Uno, Ana"), post(2, "Prueba Dos, Luis")), apply=True)
    moved = FICHA_COMPLETA.replace("piso 5, consultorio 5B", "piso 6, consultorio 6A")
    second = run(admin, export(post(1, "Prueba Uno, Ana", content=moved)), apply=False).json()
    assert (second["updated"], second["unchanged"], second["removed"]) == (1, 0, 1)
    assert second["removed_names"] == ["Prueba Dos, Luis"]
    applied = run(admin, export(post(1, "Prueba Uno, Ana", content=moved)), apply=True).json()
    assert applied["updated"] == 1
    again = run(admin, export(post(1, "Prueba Uno, Ana", content=moved))).json()
    assert (again["created"], again["updated"], again["unchanged"]) == (0, 0, 1)


def test_an_incomplete_download_does_not_wipe_the_directory(admin):
    run(admin, export(*[post(i, f"Prueba {i}, Ana") for i in range(1, 11)]), apply=True)
    partial = run(admin, export(post(1, "Prueba 1, Ana")), apply=True)
    assert partial.status_code == 409
    assert "incompleta" in partial.json()["detail"]


def test_only_doctor_cards_are_imported(admin):
    news = post(99, "Jornada de vacunación", content=p("Este sábado…"), categories=(), tags=())
    result = run(admin, export(post(1, "Prueba Uno, Ana"), news)).json()
    assert result["total"] == 1 and result["skipped_posts"] == 1
    nothing = run(admin, export(news))
    assert nothing.status_code == 400


def test_letter_can_come_from_the_css_classes(admin):
    body = {"posts": [{**post(1, "Prueba Uno, Ana", tags=()), "class_list": ["post-1", "tag-a"]}]}
    assert run(admin, body).json()["total"] == 1


def test_cards_to_review_are_listed(admin):
    vague = p("<strong>Pediatría</strong>", "Consultorio: 0212 5550006")
    result = run(
        admin, export(post(1, "Prueba Uno, Ana"), post(2, "Prueba Dos, Luis", content=vague))
    ).json()
    assert result["needs_review"] == [
        {"name": "Prueba Dos, Luis", "notes": ["No se encontró la ubicación del consultorio"]}
    ]


def test_permissions(lab_agent, supervisor, admin, anon):
    body = export(post(1, "Prueba Uno, Ana"))
    assert lab_agent.get("/api/directory").status_code == 200
    assert supervisor.get("/api/directory").status_code == 200
    assert run(lab_agent, body).status_code == 403
    assert run(supervisor, body).status_code == 403
    assert run(admin, body).status_code == 200
    assert anon.get("/api/directory").status_code == 401


def test_rejects_oversized_input(admin):
    huge = post(1, "Prueba Uno, Ana", content="x" * 70_000)
    assert run(admin, export(huge)).status_code == 422
