"""Puerto del modelo de lenguaje. El agente no sabe qué proveedor hay detrás."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMUnavailableError(Exception):
    """El modelo no respondió o su respuesta no se puede usar. El agente cae a reglas fijas."""


class LLMClient(ABC):
    @abstractmethod
    def complete_json(self, system: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Pide una respuesta que cumpla el JSON schema dado y la devuelve como dict."""
