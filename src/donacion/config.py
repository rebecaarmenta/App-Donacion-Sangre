"""Configuración de la app: se lee del entorno UNA sola vez, se valida y se pasa como objeto.

Antes cada módulo leía os.getenv por su cuenta (contenedor, fábrica del agente, main).
Ahora Settings es la única clase que conoce las variables de entorno; el resto recibe
valores ya validados por constructor (inyección de dependencias).
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Raíz del proyecto (config.py está en src/donacion/): ahí vive la base de datos por defecto.
DEFAULT_DATABASE = str(Path(__file__).resolve().parents[2] / "donacion.sqlite3")

_TRUE = ("1", "true", "si", "yes")
_FALSE = ("0", "false", "no")


@dataclass(frozen=True)
class Settings:
    use_llm: bool = True
    ollama_model: str = "llama3.2"
    ollama_host: str = "http://localhost:11434"
    ollama_timeout_seconds: float = 60.0
    token_secret: bytes | None = None
    wave_size: int = 10
    wave_wait_minutes: float = 15.0
    auto_escalate: bool = True
    escalation_check_seconds: float = 30.0
    seed_demo: bool = True
    database_path: str = DEFAULT_DATABASE   # ":memory:" = base de datos temporal (pruebas)

    def __post_init__(self) -> None:
        if self.wave_size < 1:
            raise ValueError("DONACION_WAVE_SIZE debe ser al menos 1")
        for name in ("wave_wait_minutes", "escalation_check_seconds", "ollama_timeout_seconds"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} debe ser mayor que 0")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        reader = _EnvReader(env)
        defaults = cls()
        secret = env.get("DONACION_TOKEN_SECRET")
        return cls(
            use_llm=reader.flag("DONACION_USE_LLM", defaults.use_llm),
            ollama_model=env.get("OLLAMA_MODEL", defaults.ollama_model),
            ollama_host=env.get("OLLAMA_HOST", defaults.ollama_host),
            ollama_timeout_seconds=reader.number("OLLAMA_TIMEOUT_SECONDS", defaults.ollama_timeout_seconds),
            token_secret=secret.encode() if secret else None,
            wave_size=int(reader.number("DONACION_WAVE_SIZE", defaults.wave_size)),
            wave_wait_minutes=reader.number("DONACION_WAVE_WAIT_MINUTES", defaults.wave_wait_minutes),
            auto_escalate=reader.flag("DONACION_AUTO_ESCALATE", defaults.auto_escalate),
            escalation_check_seconds=reader.number("DONACION_ESCALATION_CHECK_SECONDS",
                                                   defaults.escalation_check_seconds),
            seed_demo=reader.flag("DONACION_SEED_DEMO", defaults.seed_demo),
            database_path=env.get("DONACION_DB", defaults.database_path),
        )


class _EnvReader:
    """Convierte texto del entorno a tipos, con mensajes claros si un valor no sirve."""

    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env

    def flag(self, name: str, default: bool) -> bool:
        raw = self._env.get(name)
        if raw is None or raw.lower() == "auto":
            return default
        if raw.lower() in _TRUE:
            return True
        if raw.lower() in _FALSE:
            return False
        raise ValueError(f"{name}={raw!r}: use 1 o 0")

    def number(self, name: str, default: float) -> float:
        raw = self._env.get(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            raise ValueError(f"{name}={raw!r} no es un número") from None
