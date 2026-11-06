"""Prueba de punta a punta del flujo de la demo a través de la API."""
from fastapi.testclient import TestClient

from donacion.container import build_platform
from donacion.demo import DEMO_PASSWORD, seed_demo
from donacion.main import create_app


def make_client(clock):
    platform = build_platform(use_llm=False, clock=clock)
    seed_demo(platform)
    return TestClient(create_app(platform)), platform


def test_flujo_completo(clock):
    client, _ = make_client(clock)

    # 1. Registro + login
    new = client.post("/donors", json={
        "name": "Mariana Torres", "email": "mariana@correo.com", "password": "segura123",
        "birth_date": "2002-04-10", "weight_kg": 60, "blood_type": "A+", "lat": 20.688, "lon": -103.351,
    })
    assert new.status_code == 201
    donor_id = new.json()["id"]
    assert new.json()["eligibility"]["status"] == "pendiente"
    assert client.post("/auth/login", json={"email": "mariana@correo.com", "password": "mala"}).status_code == 401
    assert client.post("/auth/login", json={"email": "mariana@correo.com", "password": "segura123"}).status_code == 200

    # 2. Tamizaje
    screening = client.post(f"/donors/{donor_id}/screening", json={})
    assert screening.json()["status"] == "apto"

    # 3. Solicitud crítica A+
    req = client.post("/requests", json={
        "requester_name": "Familia Pérez", "blood_type": "A+", "units_needed": 2,
        "hospital_name": "Hospital Civil", "hospital_lat": 20.6866, "hospital_lon": -103.3496,
        "urgency": "critica",
    }).json()

    # 4. El agente ordena y envía la oleada
    candidates = client.get(f"/requests/{req['id']}/candidates").json()
    names = [c["name"] for c in candidates]
    assert "Gabriela Paz" not in names        # tatuaje reciente
    assert "Jorge Ríos" not in names          # peso < 50
    assert "Héctor Luna" not in names         # donó hace 30 días
    assert "Fernando Gil" not in names        # B+ incompatible
    assert all(c["blood_type"] in {"A+", "A-", "O+", "O-"} for c in candidates)

    alerts = client.post(f"/requests/{req['id']}/dispatch").json()
    assert alerts and all(a["wave"] == 1 for a in alerts)

    # 5. Confirmaciones hasta cubrir la solicitud
    for alert in alerts[:2]:
        status = client.post(f"/requests/{req['id']}/confirm", json={"donor_id": alert["donor_id"]})
        assert status.status_code == 200
    assert status.json()["status"] == "cubierta"
    assert client.post(f"/requests/{req['id']}/dispatch").status_code == 409


def test_escalamiento_envia_segunda_oleada(clock):
    client, container = make_client(clock)
    for i in range(10):  # más donantes para que haya segunda oleada
        d = client.post("/donors", json={
            "name": f"Extra {i}", "email": f"extra{i}@correo.com", "password": "segura123",
            "birth_date": "1995-01-01", "weight_kg": 70, "blood_type": "O+",
            "lat": 20.68 + i * 0.002, "lon": -103.35}).json()
        client.post(f"/donors/{d['id']}/screening", json={})
    req = client.post("/requests", json={
        "requester_name": "F", "blood_type": "O+", "units_needed": 3, "hospital_name": "H",
        "hospital_lat": 20.6866, "hospital_lon": -103.3496, "urgency": "alta"}).json()
    first = client.post(f"/requests/{req['id']}/dispatch").json()
    assert len(first) == 10

    assert client.post("/requests/escalate").json() == {}   # aún no pasan 15 minutos
    clock.advance(15)
    second = client.post("/requests/escalate").json()[req["id"]]
    assert second and all(a["wave"] == 2 for a in second)
    assert not {a["donor_id"] for a in first} & {a["donor_id"] for a in second}


def test_errores_de_validacion(clock):
    client, _ = make_client(clock)
    dup = client.post("/donors", json={
        "name": "X", "email": "donante1@demo.mx", "password": DEMO_PASSWORD, "birth_date": "1990-01-01",
        "weight_kg": 70, "blood_type": "O+", "lat": 20.6, "lon": -103.3})
    assert dup.status_code == 409
    bad = client.post("/donors", json={
        "name": "X", "email": "x@x.mx", "password": "segura123", "birth_date": "1990-01-01",
        "weight_kg": 70, "blood_type": "Z+", "lat": 20.6, "lon": -103.3})
    assert bad.status_code == 400
    assert client.get("/requests/noexiste").status_code == 404
