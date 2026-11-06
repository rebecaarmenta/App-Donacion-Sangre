from datetime import timedelta

from donacion.agent.explanation import LLMExplanation, TemplateExplanation
from donacion.agent.filters import CompatibilityFilter, EligibilityFilter, MaxDistanceFilter
from donacion.agent.matching_agent import MatchingAgent
from donacion.agent.scoring import LLMAssistedScoring, RuleBasedScoring
from donacion.agent.waves import WavePlanner
from donacion.domain.blood_request import BloodRequest, Hospital, Urgency
from donacion.domain.blood_type import BloodType
from donacion.ports.llm import LLMClient, LLMUnavailableError

from .conftest import HOSPITAL, NOW, make_donor


class FakeLLM(LLMClient):
    """Doble de prueba: devuelve respuestas fijas o falla, sin llamar a ninguna API."""

    def __init__(self, replies=None, fail=False):
        self.replies = list(replies or [])
        self.fail = fail
        self.calls = 0

    def complete_json(self, system, prompt, schema):
        self.calls += 1
        if self.fail:
            raise LLMUnavailableError("sin servicio")
        return self.replies.pop(0)


def request(blood="A+", urgency=Urgency.CRITICAL):
    return BloodRequest("r1", "Familia", BloodType.parse(blood), 2, Hospital("Hospital Civil", HOSPITAL),
                        urgency, NOW + timedelta(hours=24), NOW)


def agent(scoring=None, explainer=None, wave_size=10):
    return MatchingAgent([CompatibilityFilter(), EligibilityFilter(), MaxDistanceFilter(50)],
                         scoring or RuleBasedScoring(), WavePlanner(wave_size, 15),
                         explainer or TemplateExplanation())


def test_filtra_incompatibles_no_aptos_y_lejanos():
    donors = [make_donor("ok", "A+"), make_donor("b", "B+"), make_donor("noapto", "O+", eligible=False),
              make_donor("lejos", "O-", lat=21.5, lon=-103.35)]
    ranked = agent().rank(request("A+"), donors, NOW)
    assert [c.donor.id for c in ranked] == ["ok"]


def test_prioriza_al_mas_cercano():
    cerca, lejos = make_donor("cerca", lat=20.687, lon=-103.35), make_donor("lejos", lat=20.60, lon=-103.42)
    ranked = agent().rank(request(), [lejos, cerca], NOW)
    assert ranked[0].donor.id == "cerca"


def test_reserva_o_negativo_si_no_es_critico():
    o_neg = make_donor("oneg", "O-", lat=20.687, lon=-103.35)
    a_pos = make_donor("apos", "A+", lat=20.69, lon=-103.355)
    normal = agent().rank(request(urgency=Urgency.NORMAL), [o_neg, a_pos], NOW)
    critica = agent().rank(request(urgency=Urgency.CRITICAL), [o_neg, a_pos], NOW)
    assert normal[0].donor.id == "apos"
    assert any("O-" in r for r in normal[1].reasons)
    assert not any("reserva" in r for c in critica for r in c.reasons)


def test_oleadas_no_repiten_donantes():
    donors = [make_donor(f"d{i}", lat=20.687 + i * 0.001) for i in range(5)]
    a, req = agent(wave_size=2), request()
    first = a.plan_wave(req, donors, NOW)
    req.register_wave([x.donor_id for x in first], NOW)
    second = a.plan_wave(req, donors, NOW)
    assert len(first) == 2 and len(second) == 2
    assert not {x.donor_id for x in first} & {x.donor_id for x in second}
    assert second[0].wave == 2


def test_siguiente_oleada_solo_despues_de_la_espera():
    planner, req = WavePlanner(10, 15), request()
    assert planner.is_due(req, NOW)
    req.register_wave(["d1"], NOW)
    assert not planner.is_due(req, NOW + timedelta(minutes=10))
    assert planner.is_due(req, NOW + timedelta(minutes=15))


def test_mensaje_explica_el_motivo():
    alert = agent().plan_wave(request(), [make_donor("d1")], NOW)[0]
    assert alert.message.startswith("Hola Donante: se necesita sangre A+ (urgencia crítica)")
    assert "km del hospital" in alert.message


def test_ia_puede_reordenar_candidatos():
    donors = [make_donor("cerca", lat=20.687, lon=-103.35), make_donor("lejos", lat=20.65, lon=-103.38)]
    llm = FakeLLM([{"order": ["lejos", "cerca"], "rationale": "responde más rápido"}])
    ranked = agent(scoring=LLMAssistedScoring(llm, RuleBasedScoring())).rank(request(), donors, NOW)
    assert [c.donor.id for c in ranked] == ["lejos", "cerca"]
    assert "responde más rápido" in ranked[0].reasons[-1]


def test_si_la_ia_inventa_donantes_se_usa_el_orden_por_reglas():
    donors = [make_donor("cerca", lat=20.687, lon=-103.35), make_donor("lejos", lat=20.65, lon=-103.38)]
    llm = FakeLLM([{"order": ["lejos", "fantasma"], "rationale": "x"}])
    ranked = agent(scoring=LLMAssistedScoring(llm, RuleBasedScoring())).rank(request(), donors, NOW)
    assert [c.donor.id for c in ranked] == ["cerca", "lejos"]


def test_si_la_ia_falla_el_agente_sigue_funcionando():
    llm = FakeLLM(fail=True)
    a = agent(scoring=LLMAssistedScoring(llm, RuleBasedScoring()),
              explainer=LLMExplanation(llm, TemplateExplanation()))
    alerts = a.plan_wave(request(), [make_donor("d1"), make_donor("d2", lat=20.70)], NOW)
    assert len(alerts) == 2 and llm.calls == 2
    assert all("Te elegimos por:" in x.message for x in alerts)


def test_explicacion_con_ia():
    llm = FakeLLM([{"messages": [{"donor_id": "d1", "message": "Estás muy cerca del hospital."}]}])
    a = agent(explainer=LLMExplanation(llm, TemplateExplanation()))
    alert = a.plan_wave(request(), [make_donor("d1")], NOW)[0]
    assert alert.message.endswith("Estás muy cerca del hospital.")
