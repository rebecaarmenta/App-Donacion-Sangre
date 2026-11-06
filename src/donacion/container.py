"""Composition root: el ÚNICO lugar que conoce las clases concretas.

Aquí se decide qué reglas, filtros, estrategia de puntaje y adaptadores usa el sistema.
Cambiar memoria por una base de datos o la IA por reglas es cambiar una línea aquí.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.console_notifier import ConsoleNotifier
from .adapters.memory_alert_log import InMemoryAlertLog
from .adapters.memory_repositories import InMemoryDonorRepository, InMemoryRequestRepository
from .adapters.pbkdf2_hasher import Pbkdf2Hasher
from .adapters.system_clock import SystemClock
from .adapters.uuid_ids import UuidIdGenerator
from .agent.explanation import LLMExplanation, TemplateExplanation
from .agent.filters import CompatibilityFilter, EligibilityFilter, MaxDistanceFilter
from .agent.matching_agent import MatchingAgent
from .agent.scoring import LLMAssistedScoring, RuleBasedScoring
from .agent.waves import WavePlanner
from .ports.alert_log import AlertLog
from .ports.clock import Clock
from .ports.llm import LLMClient
from .screening.evaluator import ScreeningEvaluator
from .screening.rules import (AgeRule, DonationIntervalRule, MedicationRule, PermanentExclusionRule,
                              SurgeryRule, TattooRule, WeightRule)
from .services.donor_service import DonorService
from .services.matching_service import MatchingService
from .services.request_service import RequestService
from .services.screening_service import ScreeningService

# Parámetros del MVP (documento de visión, secciones 5 y 9).
DONATION_INTERVAL_DAYS = 56
MAX_DISTANCE_KM = 50
WAVE_SIZE = 10
WAVE_WAIT_MINUTES = 15


@dataclass
class Container:
    donors: DonorService
    screening: ScreeningService
    requests: RequestService
    matching: MatchingService
    alert_log: AlertLog
    clock: Clock
    llm_enabled: bool


def _llm_configured() -> bool:
    """DONACION_USE_LLM=1 la activa, =0 la apaga; si no se define, se usa si hay credenciales."""
    flag = os.getenv("DONACION_USE_LLM", "auto").lower()
    if flag in ("0", "false", "no"):
        return False
    if flag in ("1", "true", "si", "yes"):
        return True
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def build_container(use_llm: bool | None = None, clock: Clock | None = None,
                    llm_client: LLMClient | None = None) -> Container:
    clock = clock or SystemClock()
    donor_repo = InMemoryDonorRepository()
    request_repo = InMemoryRequestRepository()
    alert_log = InMemoryAlertLog()
    ids = UuidIdGenerator()

    evaluator = ScreeningEvaluator([
        AgeRule(min_age=18, max_age=65),
        WeightRule(min_kg=50),
        TattooRule(months=12),
        SurgeryRule(months=6),
        MedicationRule(days=5),
        DonationIntervalRule(days=DONATION_INTERVAL_DAYS),
        PermanentExclusionRule(),
    ])

    use_llm = _llm_configured() if use_llm is None else use_llm
    scoring = RuleBasedScoring()
    explainer = TemplateExplanation()
    if use_llm:
        if llm_client is None:
            from .adapters.claude_llm_client import ClaudeLLMClient
            llm_client = ClaudeLLMClient()
        scoring = LLMAssistedScoring(llm_client, base=scoring)
        explainer = LLMExplanation(llm_client, fallback=explainer)

    agent = MatchingAgent(
        filters=[CompatibilityFilter(), EligibilityFilter(), MaxDistanceFilter(MAX_DISTANCE_KM)],
        scoring=scoring,
        planner=WavePlanner(wave_size=WAVE_SIZE, wait_minutes=WAVE_WAIT_MINUTES),
        explainer=explainer,
    )

    return Container(
        donors=DonorService(donor_repo, Pbkdf2Hasher(), ids),
        screening=ScreeningService(donor_repo, evaluator, clock),
        requests=RequestService(request_repo, donor_repo, clock, DONATION_INTERVAL_DAYS, ids),
        matching=MatchingService(agent, donor_repo, request_repo, ConsoleNotifier(), alert_log, clock),
        alert_log=alert_log,
        clock=clock,
        llm_enabled=use_llm,
    )
