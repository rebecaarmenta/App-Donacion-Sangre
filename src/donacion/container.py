"""Composition root: el ÚNICO lugar que conoce las clases concretas.

PlatformBuilder recibe la configuración (Settings) y arma todo detrás de la fachada
DonationPlatform: qué reglas, qué fábrica de agente y qué adaptadores usa el sistema.
Los datos se guardan en SQLite (Settings.database_path); cambiar de base de datos o la IA por
reglas es cambiar un método aquí.
"""
from __future__ import annotations

import threading
from dataclasses import replace

from .adapters.console_notifier import ConsoleNotifier
from .adapters.hmac_tokens import HmacTokenService
from .adapters.ollama_llm_client import OllamaLLMClient
from .adapters.pbkdf2_hasher import Pbkdf2Hasher
from .adapters.retrying_notifier import RetryingNotifier
from .adapters.sqlite_database import SqliteDatabase
from .adapters.sqlite_repositories import SqliteAlertLog, SqliteDonorRepository, SqliteRequestRepository
from .adapters.system_clock import SystemClock
from .adapters.uuid_ids import UuidIdGenerator
from .agent.factory import AIAgentFactory, MatchingAgentFactory, RuleBasedAgentFactory
from .config import Settings
from .ports.clock import Clock
from .ports.llm import LLMClient
from .ports.notifier import Notifier
from .screening.evaluator import ScreeningEvaluator
from .screening.rules import (AgeRule, DonationIntervalRule, MedicationRule, PermanentExclusionRule,
                              SurgeryRule, TattooRule, WeightRule)
from .services.auth_service import AuthService
from .services.donor_service import DonorService
from .services.history_service import HistoryService
from .services.hospital_catalog import GUADALAJARA_HOSPITALS, HospitalCatalog
from .services.matching_service import MatchingService
from .services.platform import DonationPlatform
from .services.request_finder import RequestFinder
from .services.request_service import RequestService
from .services.screening_service import ScreeningService


class PlatformBuilder:
    """Arma la plataforma. clock, llm_client y notifier se pueden inyectar (p. ej. en pruebas)."""

    DONATION_INTERVAL_DAYS = 56  # NOM-253: días mínimos entre donaciones de sangre total

    def __init__(self, settings: Settings, clock: Clock | None = None,
                 llm_client: LLMClient | None = None, notifier: Notifier | None = None) -> None:
        self._settings = settings
        self._clock = clock or SystemClock()
        self._llm_client = llm_client
        self._notifier = notifier

    # ---- piezas ----
    def llm_client(self) -> LLMClient:
        """El modelo de IA es siempre Ollama (local); en pruebas se inyecta un doble."""
        if self._llm_client is None:
            s = self._settings
            self._llm_client = OllamaLLMClient(s.ollama_model, s.ollama_host, s.ollama_timeout_seconds)
        return self._llm_client

    def agent_factory(self) -> MatchingAgentFactory:
        s = self._settings
        if not s.use_llm:
            return RuleBasedAgentFactory(s.wave_size, s.wave_wait_minutes)
        return AIAgentFactory(self.llm_client(), s.wave_size, s.wave_wait_minutes)

    def fast_agent_factory(self) -> MatchingAgentFactory:
        """Solo reglas: primera oleada y vista previa de candidatos (deben ser inmediatas)."""
        return RuleBasedAgentFactory(self._settings.wave_size, self._settings.wave_wait_minutes)

    def screening_evaluator(self) -> ScreeningEvaluator:
        return ScreeningEvaluator([
            AgeRule(min_age=18, max_age=65),
            WeightRule(min_kg=50),
            TattooRule(months=12),
            SurgeryRule(months=6),
            MedicationRule(days=5),
            DonationIntervalRule(days=self.DONATION_INTERVAL_DAYS),
            PermanentExclusionRule(),
        ])

    def token_service(self, db: SqliteDatabase) -> HmacTokenService:
        # Sin DONACION_TOKEN_SECRET, la clave se genera una vez y se guarda en la base de datos:
        # las sesiones siguen valiendo al reiniciar el servidor.
        return HmacTokenService(self._settings.token_secret or db.secret("token_signing_key"), self._clock)

    def notifier(self) -> Notifier:
        return self._notifier or RetryingNotifier(ConsoleNotifier())

    # ---- todo junto ----
    def build(self) -> DonationPlatform:
        clock = self._clock
        db = SqliteDatabase(self._settings.database_path)
        donor_repo = SqliteDonorRepository(db)
        request_repo = SqliteRequestRepository(db)
        ids = UuidIdGenerator()
        finder = RequestFinder(request_repo, clock)
        donors = DonorService(donor_repo, Pbkdf2Hasher(), ids, clock, self.DONATION_INTERVAL_DAYS)
        hospitals = HospitalCatalog(GUADALAJARA_HOSPITALS)
        use_llm = self._settings.use_llm
        write_lock = threading.RLock()   # uno solo para la fachada y las oleadas

        return DonationPlatform(
            donors=donors,
            auth=AuthService(donors, self.token_service(db)),
            screening=ScreeningService(donor_repo, self.screening_evaluator(), clock),
            requests=RequestService(request_repo, finder, hospitals, clock, ids),
            history=HistoryService(donors, request_repo),
            hospitals=hospitals,
            matching=MatchingService(self.agent_factory().build(), donor_repo, request_repo, finder,
                                     self.notifier(), SqliteAlertLog(db), clock,
                                     fast_agent=self.fast_agent_factory().build(), write_lock=write_lock),
            clock=clock,
            ai_enabled=use_llm,
            ai_provider="ollama" if use_llm else None,
            write_lock=write_lock,
        )


def build_platform(use_llm: bool | None = None, clock: Clock | None = None,
                   llm_client: LLMClient | None = None, notifier: Notifier | None = None,
                   settings: Settings | None = None) -> DonationPlatform:
    """Atajo para la demo y las pruebas: Settings del entorno, con use_llm opcionalmente forzado."""
    settings = settings or Settings.from_env()
    if use_llm is not None:
        settings = replace(settings, use_llm=use_llm)
    return PlatformBuilder(settings, clock, llm_client, notifier).build()
