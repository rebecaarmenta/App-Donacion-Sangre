"""Persistencia con SQLite.

Las pruebas de contrato corren IGUAL contra memoria y contra SQLite: cualquier implementación
del puerto debe comportarse igual (sustitución de Liskov / inversión de dependencias).
"""
from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from donacion.adapters.memory_alert_log import InMemoryAlertLog
from donacion.adapters.memory_repositories import InMemoryDonorRepository, InMemoryRequestRepository
from donacion.adapters.sqlite_database import SqliteDatabase
from donacion.adapters.sqlite_repositories import (SqliteAlertLog, SqliteDonorRepository,
                                                   SqliteRequestRepository)
from donacion.config import Settings
from donacion.container import build_platform
from donacion.demo import DEMO_PASSWORD, seed_demo
from donacion.domain.alert import Alert
from donacion.domain.blood_request import BloodRequest, Hospital, RequestStatus, Urgency
from donacion.domain.blood_type import BloodType
from donacion.domain.eligibility import EligibilityResult, EligibilityStatus
from donacion.domain.errors import AuthenticationError
from donacion.main import create_app

from .conftest import HOSPITAL, NOW, make_donor


def sqlite_db():
    return SqliteDatabase(":memory:")


@pytest.fixture(params=["memoria", "sqlite"])
def repos(request):
    if request.param == "memoria":
        return InMemoryDonorRepository(), InMemoryRequestRepository(), InMemoryAlertLog()
    db = sqlite_db()
    return SqliteDonorRepository(db), SqliteRequestRepository(db), SqliteAlertLog(db)


def make_request(rid="r1", units=2):
    return BloodRequest(rid, "Familia", BloodType.parse("O-"), units, Hospital("Hospital Civil", HOSPITAL),
                        Urgency.CRITICAL, NOW + timedelta(hours=12), NOW)


# ---------- contrato de los puertos ----------
def test_contrato_donantes(repos):
    donors, _, _ = repos
    donor = make_donor("d1", blood="AB-", last_donation=date(2026, 5, 1))
    donor.update_eligibility(EligibilityResult(EligibilityStatus.DEFERRED, ("Tatuaje",), date(2027, 1, 1)))
    donor.register_alert()
    donor.record_donation(date(2026, 11, 6), date(2027, 1, 1), "r9", "Hospital Civil")
    donors.save(donor)

    loaded = donors.get("d1")
    assert (loaded.name, loaded.email, str(loaded.blood_type)) == ("Donante d1", "d1@demo.mx", "AB-")
    assert (loaded.location, loaded.birth_date, loaded.weight_kg) == (donor.location, donor.birth_date, 65)
    assert loaded.last_donation == date(2026, 11, 6)
    assert loaded.eligibility == donor.eligibility
    assert loaded.response_history == donor.response_history
    assert loaded.donations == donor.donations and loaded.donations[0].request_id == "r9"
    assert donors.find_by_email("  D1@DEMO.MX ").id == "d1"
    assert donors.find_by_email("otro@x.mx") is None and donors.get("nadie") is None

    loaded.update_profile(name="Nuevo")
    donors.save(loaded)                                     # guardar de nuevo actualiza, no duplica
    assert [d.name for d in donors.list_all()] == ["Nuevo"]


def test_contrato_solicitudes(repos):
    _, requests, _ = repos
    req = make_request()
    req.register_wave(["d1", "d2"], NOW + timedelta(minutes=1))
    req.confirm_unit("d1")
    requests.save(req)
    requests.save(make_request("r2", units=1))

    loaded = requests.get("r1")
    assert (loaded.requester_name, str(loaded.blood_type), loaded.urgency) == ("Familia", "O-", Urgency.CRITICAL)
    assert loaded.hospital == req.hospital and loaded.deadline == req.deadline
    assert loaded.notified_donors == ("d1", "d2") and loaded.confirmed_donors == ("d1",)
    assert loaded.waves_sent == 1 and loaded.last_wave_at == NOW + timedelta(minutes=1)

    loaded.confirm_unit("d2")                                # se cubre
    requests.save(loaded)
    assert requests.get("r1").status is RequestStatus.COVERED
    assert [r.id for r in requests.list_open()] == ["r2"]
    assert requests.get("nada") is None


def test_contrato_alertas(repos):
    _, _, log = repos
    a1, a2 = Alert("r1", "d1", "Ana", 1, 90.5, "hola"), Alert("r1", "d2", "Bruno", 2, 70.0, "hey")
    log.record(a1)
    log.record(a2)
    assert log.for_request("r1") == [a1, a2]
    assert log.for_donor("d2") == [a2] and log.for_donor("nadie") == []


# ---------- los datos sobreviven a un reinicio ----------
def settings_with(path):
    return replace(Settings.from_env({}), database_path=str(path), use_llm=False)


def test_los_datos_sobreviven_al_reiniciar(tmp_path, clock):
    db_file = tmp_path / "donacion.sqlite3"
    first = build_platform(settings=settings_with(db_file), clock=clock)
    seed_demo(first)
    req = first.create_request_valid_for(12, requester_name="F", blood_type="A+", units_needed=1,
                                         hospital_id="cmno", urgency="critica")
    donor_id = req.notified_donors[0]
    first.confirm_donation(req.id, donor_id)

    second = build_platform(settings=settings_with(db_file), clock=clock)   # "reinicio"
    seed_demo(second)                                                       # no duplica
    assert len(second.list_donors()) == len(first.list_donors()) == 12
    assert second.get_request(req.id).status is RequestStatus.COVERED
    assert second.alerts_for_request(req.id) == first.alerts_for_request(req.id)
    assert second.get_donor(donor_id).eligibility.status is EligibilityStatus.DEFERRED
    assert second.login("donante1@demo.mx", DEMO_PASSWORD).donor.email == "donante1@demo.mx"


def test_la_sesion_sigue_valiendo_al_reiniciar(tmp_path, clock):
    db_file = tmp_path / "donacion.sqlite3"
    first = build_platform(settings=settings_with(db_file), clock=clock)
    seed_demo(first)
    token = first.login("donante1@demo.mx", DEMO_PASSWORD).token
    second = build_platform(settings=settings_with(db_file), clock=clock)
    assert second.donor_id_from_token(token) == first.login("donante1@demo.mx", DEMO_PASSWORD).donor.id
    other = build_platform(settings=settings_with(tmp_path / "otra.sqlite3"), clock=clock)
    with pytest.raises(AuthenticationError):
        other.donor_id_from_token(token)      # otra base de datos = otra clave


def test_la_ruta_por_defecto_es_un_archivo_del_proyecto():
    default = Settings.from_env({}).database_path
    assert default.endswith("donacion.sqlite3") and "src" not in default
    assert Settings.from_env({"DONACION_DB": "/tmp/otra.db"}).database_path == "/tmp/otra.db"


def test_la_app_corre_completa_sobre_sqlite(tmp_path, clock):
    p = build_platform(settings=settings_with(tmp_path / "x.sqlite3"), clock=clock)
    seed_demo(p)
    client = TestClient(create_app(p))
    created = client.post("/requests", json={"requester_name": "F", "blood_type": "A+", "units_needed": 1,
                                             "hospital_id": "cmno", "urgency": "critica"}).json()
    assert created["waves_sent"] == 1
    alerts = client.get(f"/requests/{created['id']}/alerts",
                        headers={"X-Request-Token": created["manage_token"]}).json()
    assert alerts
    assert datetime.fromisoformat(created["deadline"]) > NOW
