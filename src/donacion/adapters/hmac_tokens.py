"""Tokens de sesión firmados con HMAC-SHA256 (biblioteca estándar, sin dependencias).

Formato: base64url(json {"sub", "aud", "exp"}) + "." + base64url(firma).
El servidor no guarda sesiones: la firma prueba que el id lo emitió él y no el navegador.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from ..domain.errors import AuthenticationError
from ..ports.clock import Clock
from ..ports.security import TokenService


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class HmacTokenService(TokenService):
    def __init__(self, secret: bytes, clock: Clock, ttl: timedelta = timedelta(hours=8)) -> None:
        if not secret:
            raise ValueError("Se necesita una clave para firmar los tokens")
        self._secret = secret
        self._clock = clock
        self._ttl = ttl

    def _sign(self, payload: str) -> str:
        return _b64encode(hmac.new(self._secret, payload.encode(), hashlib.sha256).digest())

    def issue(self, subject: str, audience: str = "donor", expires_at: datetime | None = None) -> str:
        exp = int((expires_at or self._clock.now() + self._ttl).timestamp())
        payload = _b64encode(json.dumps({"sub": subject, "aud": audience, "exp": exp}).encode())
        return f"{payload}.{self._sign(payload)}"

    def verify(self, token: str, audience: str = "donor") -> str:
        invalid = AuthenticationError("Sesión inválida o vencida: vuelve a iniciar sesión")
        try:
            payload, signature = token.split(".")
        except ValueError:
            raise invalid from None
        if not hmac.compare_digest(signature, self._sign(payload)):
            raise invalid
        try:
            data = json.loads(_b64decode(payload))
            subject, aud, exp = str(data["sub"]), data["aud"], int(data["exp"])
        except (ValueError, KeyError, TypeError):
            raise invalid from None
        if aud != audience or self._clock.now().timestamp() >= exp:
            raise invalid
        return subject
