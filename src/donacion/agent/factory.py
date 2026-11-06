"""Patrón Factory Method para construir el agente de matching.

Misma estructura que el patrón visto en clase:
1. Productos: las estrategias (ScoringStrategy, ExplanationBuilder) y sus implementaciones.
2. Clase creadora abstracta: MatchingAgentFactory, con los métodos fábrica create_scoring()
   y create_explainer(), y build(), que los usa sin saber qué clase concreta se crea.
3. Fábricas concretas: RuleBasedAgentFactory (solo reglas) y AIAgentFactory (con IA y respaldo).

Agregar otra forma de priorizar (p. ej. un modelo distinto) es crear otra fábrica concreta,
sin modificar MatchingAgent ni el resto del sistema (principio abierto/cerrado).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..ports.llm import LLMClient
from .explanation import ExplanationBuilder, LLMExplanation, TemplateExplanation
from .filters import CandidateFilter, CompatibilityFilter, EligibilityFilter, MaxDistanceFilter
from .matching_agent import MatchingAgent
from .scoring import LLMAssistedScoring, RuleBasedScoring, ScoringStrategy
from .waves import WavePlanner

# Parámetros del MVP (documento de visión, secciones 5 y 9).
MAX_DISTANCE_KM = 50
WAVE_SIZE = 10
WAVE_WAIT_MINUTES = 15


class MatchingAgentFactory(ABC):
    """Clase creadora."""

    @abstractmethod
    def create_scoring(self) -> ScoringStrategy:
        """Método fábrica: estrategia para ordenar a los candidatos."""

    @abstractmethod
    def create_explainer(self) -> ExplanationBuilder:
        """Método fábrica: cómo se redacta cada alerta."""

    def create_filters(self) -> list[CandidateFilter]:
        return [CompatibilityFilter(), EligibilityFilter(), MaxDistanceFilter(MAX_DISTANCE_KM)]

    def create_planner(self) -> WavePlanner:
        return WavePlanner(wave_size=WAVE_SIZE, wait_minutes=WAVE_WAIT_MINUTES)

    def build(self) -> MatchingAgent:
        return MatchingAgent(
            filters=self.create_filters(),
            scoring=self.create_scoring(),
            planner=self.create_planner(),
            explainer=self.create_explainer(),
        )


class RuleBasedAgentFactory(MatchingAgentFactory):
    """Fábrica concreta: agente que solo usa reglas fijas."""

    def create_scoring(self) -> ScoringStrategy:
        return RuleBasedScoring()

    def create_explainer(self) -> ExplanationBuilder:
        return TemplateExplanation()


class AIAgentFactory(MatchingAgentFactory):
    """Fábrica concreta: agente con IA y las reglas como respaldo."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def create_scoring(self) -> ScoringStrategy:
        return LLMAssistedScoring(self._llm, base=RuleBasedScoring())

    def create_explainer(self) -> ExplanationBuilder:
        return LLMExplanation(self._llm, fallback=TemplateExplanation())
