"""Brechas contra Visión y Alcances v2: primera oleada automática y rápida, escalamiento automático
y reintento de notificaciones."""
import threading
import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from donacion.adapters.escalation_scheduler import EscalationScheduler
from donacion.adapters.retrying_notifier import RetryingNotifier
from donacion.container import build_platform
from donacion.demo import seed_demo
from donacion.domain.alert import Alert
from donacion.main import create_app
from donacion.ports.notifier import NotificationError, Notifier
from donacion.domain.eligibility import ScreeningAnswers
from donacion.services.donor_service import RegisterDonorCommand

from .conftest import FakeLLM

REQUEST = {"requester_name": "Familia Pérez", "blood_type": "A+", "units_needed": 2,
           "hospital_id": "hc-fray-antonio", "urgency": "critica"}


def add_o_positive_donors(p, n=12):
    for i in range(n):
        d = p.register_donor(RegisterDonorCommand(
            name=f"Extra {i}", email=f"extra{i}@correo.com", password="segura123",
            birth_date=date(1995, 1, 1), weight_kg=70, blood_type="O+",
            lat=20.68 + i * 0.002, lon=-103.35))
        p.submit_screening(d.id, ScreeningAnswers())


# ---------- 1. la primera oleada sale sola al crear la solicitud ----------
def test_crear_la_solicitud_envia_la_primera_oleada(clock):
    platform = build_platform(use_llm=False, clock=clock)
    seed_demo(platform)
    client = TestClient(create_app(platform))
    req = client.post("/requests", json=REQUEST).json()
    assert req["waves_sent"] == 1 and req["notified_donors"]
    alerts = client.get(f"/requests/{req['id']}/alerts", headers={"X-Request-Token": req["manage_token"]}).json()
    assert alerts and {a["wave"] for a in alerts} == {1}
    assert {a["donor_id"] for a in alerts} == set(req["notified_donors"])


# ---------- 3. la primera oleada no espera a la IA; las siguientes sí la usan ----------
def test_primera_oleada_sin_ia_y_las_siguientes_con_ia(clock):
    llm = FakeLLM(fail=True)
    p = build_platform(use_llm=True, clock=clock, llm_client=llm)
    add_o_positive_donors(p)
    started = time.perf_counter()
    req = p.create_request_valid_for(12, requester_name="F", blood_type="O+", units_needed=3,
                                     hospital_id="cmno", urgency="alta")
    assert time.perf_counter() - started < 5
    assert llm.calls == 0 and req.waves_sent == 1
    clock.advance(15)
    assert p.escalate()[req.id]
    assert llm.calls > 0


# ---------- 4. reintento de notificaciones ----------
class FlakyNotifier(Notifier):
    def __init__(self, failures):
        self.failures, self.attempts, self.sent = failures, 0, []

    def send(self, alert):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise ConnectionError("sin red")
        self.sent.append(alert)


ALERT = Alert("r1", "d1", "Ana", 1, 90.0, "hola")


def test_reintenta_hasta_que_se_envia():
    inner = FlakyNotifier(failures=2)
    RetryingNotifier(inner, attempts=3, delay_seconds=0, sleep=lambda s: None).send(ALERT)
    assert inner.attempts == 3 and inner.sent == [ALERT]


def test_se_rinde_tras_los_intentos():
    inner = FlakyNotifier(failures=99)
    waits = []
    with pytest.raises(NotificationError):
        RetryingNotifier(inner, attempts=3, delay_seconds=0.5, sleep=waits.append).send(ALERT)
    assert inner.attempts == 3 and waits == [0.5, 1.0]   # espera creciente entre intentos


def test_una_notificacion_fallida_no_detiene_la_oleada(clock):
    class AlwaysFails(Notifier):
        def send(self, alert):
            raise NotificationError("caído")

    p = build_platform(use_llm=False, clock=clock, notifier=AlwaysFails())
    seed_demo(p)
    req = p.create_request_valid_for(12, requester_name="F", blood_type="A+", units_needed=1,
                                     hospital_id="cmno", urgency="critica")
    alerts = p.alerts_for_request(req.id)
    assert alerts and len(alerts) == len(req.notified_donors)   # quedan registradas y visibles en la app


# ---------- 2. escalamiento automático ----------
def test_el_programador_revisa_periodicamente_y_sobrevive_a_errores():
    calls = []
    done = threading.Event()

    def check():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("falla pasajera")
        if len(calls) >= 3:
            done.set()
        return {}

    scheduler = EscalationScheduler(check, interval_seconds=0.01)
    scheduler.start()
    assert done.wait(2)
    scheduler.stop()
    stopped_at = len(calls)
    time.sleep(0.05)
    assert len(calls) == stopped_at


def test_la_app_escala_sola_al_arrancar(clock):
    p = build_platform(use_llm=False, clock=clock)
    add_o_positive_donors(p)
    req = p.create_request_valid_for(12, requester_name="F", blood_type="O+", units_needed=3,
                                     hospital_id="cmno", urgency="alta")
    clock.advance(15)
    with TestClient(create_app(p, auto_escalate=True, escalation_check_seconds=0.01)):   # el lifespan arranca el programador
        deadline = time.time() + 2
        while p.get_request(req.id).waves_sent < 2 and time.time() < deadline:
            time.sleep(0.01)
    assert p.get_request(req.id).waves_sent == 2
