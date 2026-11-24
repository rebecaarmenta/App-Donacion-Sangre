"""Historial de donaciones del donante y su impacto (documento de visión, sección 5, punto 6)."""
from datetime import date

from fastapi.testclient import TestClient

from donacion.container import build_platform
from donacion.demo import DEMO_PASSWORD, seed_demo
from donacion.domain.donation import DonationHistory, DonationRecord
from donacion.main import create_app


def test_el_historial_cuenta_donaciones_y_solicitudes_cubiertas():
    records = (DonationRecord(date(2026, 1, 5), "r1", "Hospital Civil"),
               DonationRecord(date(2026, 6, 1), "r2", "CMNO"))
    history = DonationHistory(records, covered_request_ids=frozenset({"r2"}))
    assert history.total == 2 and history.requests_covered == 1
    assert [r.request_id for r in history.newest_first()] == ["r2", "r1"]
    assert DonationHistory((), frozenset()).total == 0


def make_client(clock):
    p = build_platform(use_llm=False, clock=clock)
    seed_demo(p)
    return TestClient(create_app(p)), p


def login(client, email):
    token = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_confirmar_agrega_la_donacion_al_historial(clock):
    client, p = make_client(clock)
    req = client.post("/requests", json={"requester_name": "F", "blood_type": "A+", "units_needed": 2,
                                         "hospital_id": "cets", "urgency": "critica"}).json()
    emails = {d.id: d.email for d in p.list_donors()}
    first, second = req["notified_donors"][:2]
    h1 = login(client, emails[first])

    empty = client.get("/me/donations", headers=h1).json()
    assert empty == {"total": 0, "requests_covered": 0, "donations": []}

    client.post(f"/requests/{req['id']}/confirm", headers=h1)
    history = client.get("/me/donations", headers=h1).json()
    assert history["total"] == 1 and history["requests_covered"] == 0      # aún falta una unidad
    assert history["donations"] == [{"date": clock.now().date().isoformat(), "request_id": req["id"],
                                     "hospital": "Centro Estatal de la Transfusión Sanguínea"}]

    client.post(f"/requests/{req['id']}/confirm", headers=login(client, emails[second]))
    assert client.get("/me/donations", headers=h1).json()["requests_covered"] == 1  # ya se cubrió


def test_el_historial_es_privado(clock):
    client, _ = make_client(clock)
    assert client.get("/me/donations").status_code == 401
