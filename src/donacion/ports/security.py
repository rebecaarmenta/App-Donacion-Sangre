"""Puerto de cifrado de contraseñas."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenService(ABC):
    """Emite y verifica tokens firmados. audience separa los usos: un token de sesión de donante
    ("donor") no sirve para manejar una solicitud ("request") ni al revés.
    verify() devuelve el sujeto y lanza AuthenticationError si el token no sirve."""

    @abstractmethod
    def issue(self, subject: str, audience: str = "donor", expires_at: datetime | None = None) -> str: ...

    @abstractmethod
    def verify(self, token: str, audience: str = "donor") -> str: ...
