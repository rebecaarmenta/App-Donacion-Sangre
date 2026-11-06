"""Estrategias de priorización: deciden en qué ORDEN avisar a los candidatos."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from ..domain.alert import RankedCandidate
from ..domain.blood_request import BloodRequest, Urgency
from ..domain.donor import Donor
from ..ports.llm import LLMClient, LLMUnavailableError

log = logging.getLogger(__name__)


class ScoringStrategy(ABC):
    @abstractmethod
    def rank(self, donors: list[Donor], request: BloodRequest) -> list[RankedCandidate]:
        """Devuelve los candidatos ordenados del más al menos prioritario."""


class RuleBasedScoring(ScoringStrategy):
    """Puntaje determinista. También es el respaldo cuando la IA no está disponible."""

    def __init__(self, reference_km: float = 30.0) -> None:
        self._reference_km = reference_km

    def rank(self, donors, request):
        ranked = [self._score(d, request) for d in donors]
        return sorted(ranked, key=lambda c: (-c.score, c.distance_km))

    def _score(self, donor: Donor, request: BloodRequest) -> RankedCandidate:
        distance = donor.location.distance_km(request.hospital.location)
        proximity = max(0.0, 1 - distance / self._reference_km)
        exact_match = donor.blood_type == request.blood_type
        reasons = [f"a {distance:.1f} km del hospital"]

        if exact_match:
            reasons.append(f"mismo tipo de sangre ({donor.blood_type})")
        else:
            reasons.append(f"sangre {donor.blood_type} compatible con {request.blood_type}")
        if donor.last_donation is None:
            reasons.append("sin donaciones registradas")
        else:
            reasons.append(f"última donación: {donor.last_donation.isoformat()}")

        score = 45 * proximity + 25 * (1.0 if exact_match else 0.6) + 30 * donor.response_rate

        # Reservar O- (donante universal) para casos críticos o pacientes O-.
        if (donor.blood_type.is_universal_donor() and not request.blood_type.is_universal_donor()
                and request.urgency is not Urgency.CRITICAL):
            score -= 20
            reasons.append("sangre O- reservada para casos críticos")

        return RankedCandidate(donor, round(max(score, 0.0), 1), round(distance, 1), tuple(reasons))


_RERANK_SYSTEM = """Eres el agente de priorización de una plataforma de donación voluntaria de sangre.
Recibes una solicitud y una lista de candidatos que YA son compatibles y aptos para donar.
Tu tarea es decidir en qué orden avisarles para cubrir la solicitud lo antes posible.

Criterios:
- Con urgencia crítica pesa más la cercanía y la tasa de respuesta.
- Reserva a los donantes O- cuando el paciente no es O- y la urgencia no es crítica.
- Prefiere el mismo tipo de sangre cuando las demás condiciones son parecidas.
- El puntaje base es una referencia, no una obligación.

No decides si alguien puede donar: eso ya lo resolvieron reglas médicas.
Devuelve TODOS los donor_id recibidos, cada uno una sola vez, en el nuevo orden,
y una justificación breve en español."""

_RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "order": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["order", "rationale"],
    "additionalProperties": False,
}


class LLMAssistedScoring(ScoringStrategy):
    """Ordena con reglas y le pide al modelo que reordene los mejores candidatos.

    Si el modelo falla o devuelve algo inválido, se usa el orden de la estrategia base
    (tolerancia a fallos, sección 7 del documento de visión).
    """

    def __init__(self, llm: LLMClient, base: ScoringStrategy, top_n: int = 15) -> None:
        self._llm = llm
        self._base = base
        self._top_n = top_n

    def rank(self, donors, request):
        base_ranking = self._base.rank(donors, request)
        if len(base_ranking) < 2:
            return base_ranking
        head, tail = base_ranking[: self._top_n], base_ranking[self._top_n:]
        try:
            reply = self._llm.complete_json(_RERANK_SYSTEM, self._prompt(head, request), _RERANK_SCHEMA)
            reordered = self._apply_order(head, reply)
        except LLMUnavailableError as exc:
            log.warning("Reordenamiento con IA no disponible, se usa el orden por reglas: %s", exc)
            return base_ranking
        return reordered + tail

    @staticmethod
    def _prompt(candidates: list[RankedCandidate], request: BloodRequest) -> str:
        # Solo datos necesarios para decidir: sin nombres, correos ni ubicación exacta.
        payload = {
            "solicitud": {
                "tipo_sangre": str(request.blood_type),
                "unidades": request.units_needed - request.units_confirmed,
                "urgencia": request.urgency.value,
            },
            "candidatos": [
                {
                    "donor_id": c.donor.id,
                    "tipo_sangre": str(c.donor.blood_type),
                    "distancia_km": c.distance_km,
                    "tasa_respuesta": round(c.donor.response_rate, 2),
                    "puntaje_base": c.score,
                }
                for c in candidates
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _apply_order(candidates: list[RankedCandidate], reply: dict) -> list[RankedCandidate]:
        order = reply.get("order", [])
        by_id = {c.donor.id: c for c in candidates}
        if sorted(order) != sorted(by_id):
            raise LLMUnavailableError("El orden devuelto no contiene exactamente los mismos candidatos")
        note = f"orden ajustado por el agente: {reply.get('rationale', '').strip()}"
        return [
            RankedCandidate(by_id[i].donor, by_id[i].score, by_id[i].distance_km, by_id[i].reasons + (note,))
            for i in order
        ]
