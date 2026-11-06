"""Constructores del mensaje de cada alerta: explican al donante POR QUÉ se le avisa."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..domain.alert import RankedCandidate
from ..domain.blood_request import BloodRequest
from ..ports.llm import LLMClient, LLMUnavailableError
from .prompts import ExplanationPromptBuilder

log = logging.getLogger(__name__)


def _greeting(candidate: RankedCandidate, request: BloodRequest) -> str:
    first_name = candidate.donor.name.split()[0]
    return (f"Hola {first_name}: se necesita sangre {request.blood_type} "
            f"(urgencia {request.urgency.label}) en {request.hospital.name}.")


class ExplanationBuilder(ABC):
    @abstractmethod
    def explain(self, wave: list[RankedCandidate], request: BloodRequest) -> dict[str, str]:
        """Devuelve {donor_id: mensaje} para todos los candidatos de la oleada."""


class TemplateExplanation(ExplanationBuilder):
    """Mensaje armado con plantilla a partir de las razones del puntaje."""

    def explain(self, wave, request):
        messages = {}
        for c in wave:
            reasons = ", ".join(r for r in c.reasons if not r.startswith("orden ajustado"))
            messages[c.donor.id] = f"{_greeting(c, request)} Te elegimos por: {reasons}."
        return messages


class LLMExplanation(ExplanationBuilder):
    """Pide al modelo una explicación por candidato; si falla usa el respaldo."""

    def __init__(self, llm: LLMClient, fallback: ExplanationBuilder,
                 prompts: ExplanationPromptBuilder = ExplanationPromptBuilder()) -> None:
        self._llm = llm
        self._fallback = fallback
        self._prompts = prompts

    def explain(self, wave, request):
        if not wave:
            return {}
        try:
            reply = self._llm.complete_json(self._prompts.system, self._prompts.build(wave, request),
                                            self._prompts.schema)
            texts = {m["donor_id"]: m["message"].strip() for m in reply.get("messages", [])}
            if set(texts) != {c.donor.id for c in wave} or not all(texts.values()):
                raise LLMUnavailableError("Faltan mensajes o hay donantes de más")
        except LLMUnavailableError as exc:
            log.warning("Explicación con IA no disponible, se usa la plantilla: %s", exc)
            return self._fallback.explain(wave, request)
        return {c.donor.id: f"{_greeting(c, request)} {texts[c.donor.id]}" for c in wave}
