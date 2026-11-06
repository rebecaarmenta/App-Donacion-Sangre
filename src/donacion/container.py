"""Composition root: el ÚNICO lugar que conoce las clases concretas.

Aquí se decide qué reglas, qué fábrica de agente y qué adaptadores usa el sistema, y se
entrega todo armado detrás de la fachada DonationPlatform. Cambiar memoria por una base
de datos o la IA por reglas es cambiar una línea aquí.
"""
from __future__ import annotations

import os

from .adapters.console_notifier import ConsoleNotifier
from .adapters.memory_alert_log import InMemoryAlertLog
from .adapters.memory_repositories import InMemoryDonorRepository, InMemoryRequestRepository
from .adapters.pbkdf2_hasher import Pbkdf2Hasher
from .adapters.system_clock import SystemClock
from .adapters.uuid_ids import UuidIdGenerator
from .agent.factory import AIAgentFactory, MatchingAgentFactory, RuleBasedAgentFactory
from .ports.clock import Clock
from .ports.llm import LLMClient
from .screening.evaluator import ScreeningEvaluator
from .screening.rules import (AgeRule, DonationIntervalRule, MedicationRule, PermanentExclusionRule,
                              SurgeryRule, TattooRule, WeightRule)
from .services.donor_service import DonorService
from .services.matching_service import MatchingService
from .services.platform import DonationPlatform
from .services.request_finder import RequestFinder
from .services.request_service import RequestService
from .services.screening_service import ScreeningService

DONATION_INTERVAL_DAYS = 56


def _llm_configured() -> bool:
    """DONACION_USE_LLM=1 la activa, =0 la apaga; si no se define, se usa si hay credenciales."""
    flag = os.getenv("DONACION_USE_LLM", "auto").lower()
    if flag in ("0", "false", "no"):
        return False
    if flag in ("1", "true", "si", "yes"):
        return True
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _agent_factory(use_llm: bool, llm_client: LLMClient | None) -> MatchingAgentFactory:
    if not use_llm:
        return RuleBasedAgentFactory()
    if llm_client is None:
        from .adapters.claude_llm_client import ClaudeLLMClient
        llm_client = ClaudeLLMClient()
    return AIAgentFactory(llm_client)


def _screening_evaluator() -> ScreeningEvaluator:
    return ScreeningEvaluator([
        AgeRule(min_age=18, max_age=65),
        WeightRule(min_kg=50),
        TattooRule(months=12),
        SurgeryRule(months=6),
        MedicationRule(days=5),
        DonationIntervalRule(days=DONATION_INTERVAL_DAYS),
        PermanentExclusionRule(),
    ])


def build_platform(use_llm: bool | None = None, clock: Clock | None = None,
                   llm_client: LLMClient | None = None) -> DonationPlatform:
    clock = clock or SystemClock()
    use_llm = _llm_configured() if use_llm is None else use_llm

    donor_repo = InMemoryDonorRepository()
    request_repo = InMemoryRequestRepository()
    ids = UuidIdGenerator()
    finder = RequestFinder(request_repo, clock)
    agent = _agent_factory(use_llm, llm_client).build()

    return DonationPlatform(
        donors=DonorService(donor_repo, Pbkdf2Hasher(), ids),
        screening=ScreeningService(donor_repo, _screening_evaluator(), clock),
        requests=RequestService(request_repo, finder, donor_repo, clock, DONATION_INTERVAL_DAYS, ids),
        matching=MatchingService(agent, donor_repo, request_repo, finder, ConsoleNotifier(),
                                 InMemoryAlertLog(), clock),
        clock=clock,
        ai_enabled=use_llm,
    )
