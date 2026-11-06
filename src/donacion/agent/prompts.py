"""Constructores de prompts para el modelo de IA.

Extraídos de LLMAssistedScoring y LLMExplanation (refactorización Extract Class):
decidir el orden o redactar mensajes es una responsabilidad; armar el texto para el
modelo es otra. También concentran la regla de privacidad: al modelo nunca se le
envían nombres, correos ni ubicaciones exactas.
"""
from __future__ import annotations

import json
from typing import Any

from ..domain.alert import RankedCandidate
from ..domain.blood_request import BloodRequest


class RerankPromptBuilder:
    system = """Eres el agente de priorización de una plataforma de donación voluntaria de sangre.
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

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "order": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
        "required": ["order", "rationale"],
        "additionalProperties": False,
    }

    def build(self, candidates: list[RankedCandidate], request: BloodRequest) -> str:
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


class ExplanationPromptBuilder:
    system = """Redactas alertas para donantes voluntarios de sangre.
Para cada candidato escribe UNA oración breve, cálida y en español, en segunda persona (tú),
que explique por qué se le eligió, usando solo los datos recibidos (no inventes nada ni des consejos médicos).
No incluyas saludo: el sistema lo agrega. Devuelve un mensaje por cada donor_id recibido."""

    schema: dict[str, Any] = {
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

    def build(self, wave: list[RankedCandidate], request: BloodRequest) -> str:
        payload = {
            "solicitud": {"tipo_sangre": str(request.blood_type), "urgencia": request.urgency.label,
                          "hospital": request.hospital.name},
            "candidatos": [{"donor_id": c.donor.id, "razones": list(c.reasons)} for c in wave],
        }
        return json.dumps(payload, ensure_ascii=False)
