"""Adaptador del puerto LLMClient con Claude (SDK oficial de Anthropic).

- Modelo: Claude Opus 5.5.
- Respuesta en JSON validado con structured outputs (output_config.format).
- Esfuerzo bajo: son decisiones cortas y la alerta debe salir rápido.
- Respaldo del lado del servidor (fallbacks="default") por si el modelo declina la petición.
Cualquier falla se convierte en LLMUnavailableError y el agente usa las reglas fijas.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from ..ports.llm import LLMClient, LLMUnavailableError

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"


class ClaudeLLMClient(LLMClient):
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "low",
                 timeout_seconds: float = 30.0, client: anthropic.Anthropic | None = None) -> None:
        # Sin api_key explícita: el SDK la toma de ANTHROPIC_API_KEY (o del perfil de `ant auth login`).
        self._client = client or anthropic.Anthropic(timeout=timeout_seconds, max_retries=1)
        self._model = model
        self._effort = effort

    def complete_json(self, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": self._effort, "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.RateLimitError as exc:
            raise LLMUnavailableError(f"Límite de uso alcanzado: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMUnavailableError(f"Error de la API ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMUnavailableError("Sin conexión con la API de Claude") from exc

        if response.stop_reason != "end_turn":
            raise LLMUnavailableError(f"Respuesta incompleta (stop_reason={response.stop_reason})")

        text = "".join(block.text for block in response.content if block.type == "text")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError("La respuesta no es JSON válido") from exc
        if not isinstance(data, dict):
            raise LLMUnavailableError("La respuesta no es un objeto JSON")
        log.debug("Claude respondió (request_id=%s)", response._request_id)
        return data
