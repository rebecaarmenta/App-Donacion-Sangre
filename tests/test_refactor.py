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


# ---------- Task 2: Introduce Parameter Object ScoringWeights ----------
def test_pesos_por_defecto_conservan_el_orden():
    from donacion.agent.weights import ScoringWeights
    donors = [make_donor("a", lat=20.687, lon=-103.35), make_donor("b", "O+", lat=20.70, lon=-103.38),
              make_donor("c", "O-", lat=20.69, lon=-103.351), make_donor("d", "A-", lat=20.62, lon=-103.42)]
    before = [(c.donor.id, c.score) for c in RuleBasedScoring().rank(donors, a_request())]
    after = [(c.donor.id, c.score) for c in RuleBasedScoring(ScoringWeights()).rank(donors, a_request())]
    assert after == before


def test_pesos_configurables_cambian_la_prioridad():
    from donacion.agent.weights import ScoringWeights
    cerca = make_donor("cerca", lat=20.687, lon=-103.35)            # tasa 0.5 (sin historial)
    lejos = make_donor("lejos", lat=20.55, lon=-103.45)              # ~18 km
    for _ in range(2):
        lejos.register_alert()
        lejos.record_donation(date(2026, 1, 1), date(2026, 3, 1))     # tasa 1.0
    assert RuleBasedScoring().rank([cerca, lejos], a_request())[0].donor.id == "cerca"
    only_response = ScoringWeights(proximity=0, blood_match=0, response=100)
    assert RuleBasedScoring(only_response).rank([cerca, lejos], a_request())[0].donor.id == "lejos"
