"""Pruebas que respaldan las refactorizaciones (docs/refactorizacion.md)."""
from datetime import date, timedelta

from donacion.adapters.console_notifier import ConsoleNotifier
from donacion.adapters.memory_alert_log import InMemoryAlertLog
from donacion.adapters.memory_repositories import InMemoryDonorRepository, InMemoryRequestRepository
from donacion.adapters.pbkdf2_hasher import Pbkdf2Hasher
from donacion.agent.explanation import TemplateExplanation
from donacion.agent.filters import CompatibilityFilter, EligibilityFilter
from donacion.agent.matching_agent import MatchingAgent
from donacion.agent.scoring import RuleBasedScoring
from donacion.agent.waves import WavePlanner
from donacion.domain.blood_request import BloodRequest, Hospital, Urgency
from donacion.domain.blood_type import BloodType
from donacion.ports.ids import IdGenerator
from donacion.ports.notifier import Notifier
from donacion.services.donor_service import DonorService, RegisterDonorCommand
from donacion.services.matching_service import MatchingService

from .conftest import HOSPITAL, NOW, make_donor


class SpyNotifier(Notifier):
    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)


class SequentialIds(IdGenerator):
    def __init__(self, prefix):
        self.prefix, self.n = prefix, 0

    def new_id(self):
        self.n += 1
        return f"{self.prefix}{self.n}"


def a_request(blood="A+", hours=24):
    return BloodRequest("r1", "Familia", BloodType.parse(blood), 1, Hospital("Hospital Civil", HOSPITAL),
                        Urgency.CRITICAL, NOW + timedelta(hours=hours), NOW)


# ---------- Task 1: inversión de dependencias ----------
def test_las_alertas_se_registran_en_el_log_y_no_en_el_notificador(clock):
    donors, requests = InMemoryDonorRepository(), InMemoryRequestRepository()
    donor = make_donor("d1")
    donors.save(donor)
    request = a_request()
    requests.save(request)
    spy, alert_log = SpyNotifier(), InMemoryAlertLog()
    agent = MatchingAgent([CompatibilityFilter(), EligibilityFilter()], RuleBasedScoring(),
                          WavePlanner(10, 15), TemplateExplanation())
    matching = MatchingService(agent, donors, requests, spy, alert_log, clock)

    alerts = matching.dispatch(request.id)

    assert spy.sent == alerts
    assert matching.alerts_for_donor(donor.id) == alerts
    assert alert_log.for_request(request.id) == alerts


def test_ids_inyectados():
    service = DonorService(InMemoryDonorRepository(), Pbkdf2Hasher(), SequentialIds("d"))
    donor = service.register(RegisterDonorCommand(
        name="Ana López", email="ana@demo.mx", password="segura123", birth_date=date(2000, 1, 1),
        weight_kg=60, blood_type="O+", lat=20.67, lon=-103.34))
    assert donor.id == "d1"


def test_console_notifier_solo_envia():
    assert not hasattr(ConsoleNotifier(), "sent_to")


# ---------- Task 2: Extract Class ResponseHistory ----------
def test_historial_de_respuesta_es_inmutable_y_calcula_la_tasa():
    from donacion.domain.response_history import ResponseHistory
    h = ResponseHistory()
    assert h.rate == 0.5
    h2 = h.with_alert().with_alert().with_acceptance()
    assert (h.received, h2.received, h2.accepted, h2.rate) == (0, 2, 1, 0.5)


def test_donante_expone_su_historial():
    donor = make_donor("d1")
    donor.register_alert()
    donor.record_donation(date(2026, 1, 1), date(2026, 3, 1))
    assert (donor.response_history.received, donor.response_history.accepted) == (1, 1)
    assert donor.response_rate == 1.0
