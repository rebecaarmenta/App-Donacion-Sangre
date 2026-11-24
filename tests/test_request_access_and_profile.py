"""Token de la solicitud, edición del perfil y "Ver candidatos" rápido."""
from fastapi.testclient import TestClient

from donacion.container import build_platform
from donacion.demo import DEMO_PASSWORD, seed_demo
from donacion.main import create_app

from .conftest import FakeLLM

REQUEST = {"requester_name": "Familia Pérez", "blood_type": "A+", "units_needed": 2,
           "hospital_id": "hc-fray-antonio", "urgency": "critica"}


def make_client(clock, **kwargs):
    platform = build_platform(clock=clock, **{"use_llm": False, **kwargs})
    seed_demo(platform)
    return TestClient(create_app(platform)), platform


def bearer(client, email="donante1@demo.mx", password=DEMO_PASSWORD):
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- 2. solo quien creó la solicitud la maneja ----------
def test_crear_entrega_un_token_para_manejar_la_solicitud(clock):
    client, _ = make_client(clock)
    created = client.post("/requests", json=REQUEST).json()
    assert created["manage_token"]
    rid, own = created["id"], {"X-Request-Token": created["manage_token"]}
    assert client.get(f"/requests/{rid}/candidates", headers=own).status_code == 200
    assert client.get(f"/requests/{rid}/alerts", headers=own).status_code == 200
    assert client.post(f"/requests/{rid}/dispatch", headers=own).status_code == 200


def test_sin_token_o_con_el_de_otra_solicitud_no_se_puede(clock):
    client, _ = make_client(clock)
    a = client.post("/requests", json=REQUEST).json()
    b = client.post("/requests", json=REQUEST).json()
    for path, method in [("candidates", "get"), ("alerts", "get"), ("dispatch", "post")]:
        url = f"/requests/{a['id']}/{path}"
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers={"X-Request-Token": "falso"}).status_code == 401
        assert getattr(client, method)(url, headers={"X-Request-Token": b["manage_token"]}).status_code == 403
        # el token de sesión de un donante tampoco sirve para manejar solicitudes
        donor_token = bearer(client)["Authorization"].split()[1]
        assert getattr(client, method)(url, headers={"X-Request-Token": donor_token}).status_code == 401


def test_el_token_de_la_solicitud_no_abre_sesion_de_donante(clock):
    client, _ = make_client(clock)
    created = client.post("/requests", json=REQUEST).json()
    assert client.get("/me", headers={"Authorization": f"Bearer {created['manage_token']}"}).status_code == 401


def test_el_estado_publico_no_lleva_el_token(clock):
    client, _ = make_client(clock)
    created = client.post("/requests", json=REQUEST).json()
    assert "manage_token" not in client.get(f"/requests/{created['id']}").json()


# ---------- 3. editar el perfil ----------
def test_editar_ubicacion_y_nombre_conserva_la_elegibilidad(clock):
    client, _ = make_client(clock)
    h = bearer(client)
    assert client.get("/me", headers=h).json()["eligibility"]["status"] == "apto"
    r = client.patch("/me", headers=h, json={"name": "Ana María López", "lat": 20.72, "lon": -103.39})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Ana María López" and (body["lat"], body["lon"]) == (20.72, -103.39)
    assert body["eligibility"]["status"] == "apto"


def test_cambiar_peso_o_ultima_donacion_pide_repetir_el_cuestionario(clock):
    client, _ = make_client(clock)
    h = bearer(client)
    r = client.patch("/me", headers=h, json={"weight_kg": 45})
    assert r.json()["weight_kg"] == 45
    assert r.json()["eligibility"]["status"] == "pendiente"     # ya no aparece como apto
    assert client.post("/me/screening", headers=h, json={}).json()["status"] == "no_apto"

    h5 = bearer(client, "donante5@demo.mx")
    r = client.patch("/me", headers=h5, json={"last_donation": "2026-10-20"})
    assert r.json()["last_donation"] == "2026-10-20" and r.json()["eligibility"]["status"] == "pendiente"


def test_validaciones_del_perfil(clock):
    client, _ = make_client(clock)
    h = bearer(client)
    assert client.patch("/me", json={"name": "X"}).status_code == 401
    assert client.patch("/me", headers=h, json={"weight_kg": 0}).status_code == 422
    assert client.patch("/me", headers=h, json={"name": "  "}).status_code == 400
    assert client.patch("/me", headers=h, json={"last_donation": "2030-01-01"}).status_code == 400
    assert client.patch("/me", headers=h, json={"lat": 20.7}).status_code == 400          # lat sin lon
    assert client.patch("/me", headers=h, json={"blood_type": "O-"}).status_code == 422   # no editable
    assert client.patch("/me", headers=h, json={"email": "otro@x.mx"}).status_code == 422


def test_editar_sin_cambios_no_toca_la_elegibilidad(clock):
    client, _ = make_client(clock)
    h = bearer(client)
    me = client.get("/me", headers=h).json()
    r = client.patch("/me", headers=h, json={"weight_kg": me["weight_kg"]})
    assert r.json()["eligibility"]["status"] == "apto"


# ---------- 4. "Ver candidatos" no espera al modelo de IA ----------
def test_ver_candidatos_usa_reglas(clock):
    llm = FakeLLM(fail=True)
    client, _ = make_client(clock, use_llm=True, llm_client=llm)
    created = client.post("/requests", json=REQUEST).json()
    r = client.get(f"/requests/{created['id']}/candidates", headers={"X-Request-Token": created["manage_token"]})
    assert r.status_code == 200 and r.json()
    assert llm.calls == 0
