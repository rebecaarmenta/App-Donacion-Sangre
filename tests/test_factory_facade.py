"""Pruebas de los patrones Factory Method (agente) y Facade (plataforma)."""
from datetime import timedelta
from pathlib import Path

from donacion.agent.explanation import LLMExplanation
from donacion.agent.factory import AIAgentFactory, MatchingAgentFactory, RuleBasedAgentFactory
from donacion.agent.matching_agent import MatchingAgent
from donacion.agent.scoring import LLMAssistedScoring, RuleBasedScoring
from donacion.container import build_platform
from donacion.domain.blood_request import BloodRequest, Hospital, Urgency
from donacion.domain.blood_type import BloodType
from donacion.services.platform import DonationPlatform

from .conftest import HOSPITAL, NOW, FakeLLM, make_donor

ROUTES = Path(__file__).resolve().parents[1] / "src" / "donacion" / "api" / "routes.py"


def request():
    return BloodRequest("r1", "Familia", BloodType.parse("A+"), 1, Hospital("Hospital Civil", HOSPITAL),
                        Urgency.CRITICAL, NOW + timedelta(hours=24), NOW)


def test_fabrica_por_reglas_crea_agente_sin_ia():
    factory = RuleBasedAgentFactory()
    assert isinstance(factory, MatchingAgentFactory)
    assert isinstance(factory.build(), MatchingAgent)
    assert isinstance(factory.create_scoring(), RuleBasedScoring)


def test_fabrica_con_ia_crea_estrategias_con_respaldo():
    factory = AIAgentFactory(FakeLLM(fail=True))
    assert isinstance(factory.create_scoring(), LLMAssistedScoring)
    assert isinstance(factory.create_explainer(), LLMExplanation)


def test_las_fabricas_son_intercambiables():
    for factory in (RuleBasedAgentFactory(), AIAgentFactory(FakeLLM(fail=True))):
        alerts = factory.build().plan_wave(request(), [make_donor("d1")], NOW)
        assert [a.donor_id for a in alerts] == ["d1"]


def test_build_platform_elige_la_fabrica():
    assert isinstance(build_platform(use_llm=False), DonationPlatform)
    assert build_platform(use_llm=False).ai_enabled is False
    assert build_platform(use_llm=True, llm_client=FakeLLM(fail=True)).ai_enabled is True


def test_la_api_solo_depende_de_la_fachada():
    source = ROUTES.read_text()
    assert "DonationPlatform" in source
    for concrete in ("DonorService", "MatchingService", "RequestService", "ScreeningService", "adapters"):
        assert concrete not in source
    imports = [line for line in source.splitlines() if line.startswith(("from ", "import "))]
    service_imports = [line for line in imports if "services" in line]
    assert service_imports == ["from ..services.platform import DonationPlatform, RegisterDonorCommand"]


def test_espera_entre_oleadas_configurable_para_la_demo(monkeypatch):
    monkeypatch.setenv("DONACION_WAVE_WAIT_MINUTES", "0.25")   # 15 segundos
    planner = RuleBasedAgentFactory().create_planner()
    req = request()
    req.register_wave(["d1"], NOW)
    assert not planner.is_due(req, NOW + timedelta(seconds=10))
    assert planner.is_due(req, NOW + timedelta(seconds=15))


def test_espera_por_defecto_es_15_minutos(monkeypatch):
    monkeypatch.delenv("DONACION_WAVE_WAIT_MINUTES", raising=False)
    planner = RuleBasedAgentFactory().create_planner()
    req = request()
    req.register_wave(["d1"], NOW)
    assert not planner.is_due(req, NOW + timedelta(minutes=14))
    assert planner.is_due(req, NOW + timedelta(minutes=15))


def test_tamano_de_oleada_configurable_para_la_demo(monkeypatch):
    monkeypatch.setenv("DONACION_WAVE_SIZE", "3")
    donors = [make_donor(f"d{i}", lat=20.687 + i * 0.001) for i in range(5)]
    alerts = RuleBasedAgentFactory().build().plan_wave(request(), donors, NOW)
    assert len(alerts) == 3
