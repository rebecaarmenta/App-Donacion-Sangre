"""Cifrado de contraseñas con PBKDF2-SHA256 (biblioteca estándar, sin dependencias)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from ..ports.security import PasswordHasher


class Pbkdf2Hasher(PasswordHasher):
    def __init__(self, iterations: int = 200_000) -> None:
        self._iterations = iterations

    def hash(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), self._iterations)
        return f"pbkdf2_sha256${self._iterations}${salt}${digest.hex()}"

    def verify(self, password: str, hashed: str) -> bool:
        try:
            _, iterations, salt, expected = hashed.split("$")
        except ValueError:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
