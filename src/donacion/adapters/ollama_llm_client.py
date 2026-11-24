"""Adaptador del puerto LLMClient con Ollama (modelo local: sin costo por token).

- Llama a POST {host}/api/chat con stream=false.
- Respuesta en JSON validado con structured outputs de Ollama ("format": <JSON schema>).
- temperature 0: el orden y los mensajes deben ser estables entre llamadas.
- Usa solo la biblioteca estándar (urllib), sin dependencias nuevas.
Cualquier falla (Ollama apagado, modelo no descargado, JSON inválido) se convierte en
LLMUnavailableError y el agente usa las reglas fijas.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Callable

from ..ports.llm import LLMClient, LLMUnavailableError

log = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"

PostFn = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_post(timeout_seconds: float) -> PostFn:
    def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            try:
                return {"error": json.loads(body).get("error", body)}
            except ValueError:
                return {"error": f"HTTP {exc.code}: {body}"}
    return post


class OllamaLLMClient(LLMClient):
    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST,
                 timeout_seconds: float = 60.0, post: PostFn | None = None) -> None:
        self._model = model
        self._url = host.rstrip("/") + "/api/chat"
        self._post = post or _http_post(timeout_seconds)

    @property
    def model(self) -> str:
        return self._model

    @property
    def url(self) -> str:
        return self._url

    def complete_json(self, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        }
        try:
            response = self._post(self._url, payload)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise LLMUnavailableError(f"Sin conexión con Ollama en {self._url}: {exc}") from exc

        if "error" in response:
            raise LLMUnavailableError(f"Ollama respondió con error: {response['error']}")
        if response.get("done_reason") not in (None, "stop"):
            raise LLMUnavailableError(f"Respuesta incompleta (done_reason={response.get('done_reason')})")

        text = (response.get("message") or {}).get("content", "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMUnavailableError("La respuesta no es JSON válido") from exc
        if not isinstance(data, dict):
            raise LLMUnavailableError("La respuesta no es un objeto JSON")
        log.debug("Ollama (%s) respondió", self._model)
        return data
