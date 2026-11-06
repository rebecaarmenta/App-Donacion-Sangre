"""Constructores del mensaje de cada alerta: explican al donante POR QUÉ se le avisa."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from ..domain.alert import RankedCandidate
from ..domain.blood_request import BloodRequest
from ..ports.llm import LLMClient, LLMUnavailableError

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


_EXPLAIN_SYSTEM = """Redactas alertas para donantes voluntarios de sangre.
Para cada candidato escribe UNA oración breve, cálida y en español, en segunda persona (tú),
que explique por qué se le eligió, usando solo los datos recibidos (no inventes nada ni des consejos médicos).
No incluyas saludo: el sistema lo agrega. Devuelve un mensaje por cada donor_id recibido."""

_EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"donor_id": {"type": "string"}, "message": {"type": "string"}},
                "required": ["donor_id", "message"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["messages"],
    "additionalProperties": False,
}


class LLMExplanation(ExplanationBuilder):
    """Pide al modelo una explicación por candidato; si falla usa el respaldo."""

    def __init__(self, llm: LLMClient, fallback: ExplanationBuilder) -> None:
        self._llm = llm
        self._fallback = fallback

    def explain(self, wave, request):
        if not wave:
            return {}
        payload = {
            "solicitud": {"tipo_sangre": str(request.blood_type), "urgencia": request.urgency.label,
                          "hospital": request.hospital.name},
            "candidatos": [{"donor_id": c.donor.id, "razones": list(c.reasons)} for c in wave],
        }
        try:
            reply = self._llm.complete_json(_EXPLAIN_SYSTEM, json.dumps(payload, ensure_ascii=False),
                                            _EXPLAIN_SCHEMA)
            texts = {m["donor_id"]: m["message"].strip() for m in reply.get("messages", [])}
            if set(texts) != {c.donor.id for c in wave} or not all(texts.values()):
                raise LLMUnavailableError("Faltan mensajes o hay donantes de más")
        except LLMUnavailableError as exc:
            log.warning("Explicación con IA no disponible, se usa la plantilla: %s", exc)
            return self._fallback.explain(wave, request)
        return {c.donor.id: f"{_greeting(c, request)} {texts[c.donor.id]}" for c in wave}
