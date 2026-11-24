"""Caso de uso: credenciales firmadas.

- Sesión del donante: se obtiene con correo y contraseña; identifica al donante.
- Token de la solicitud: se entrega a quien crea la solicitud (no tiene cuenta) y es lo único que
  permite ver sus candidatos y alertas o adelantar oleadas. Sin él, cualquiera con el id podría
  mandar alertas de más a los donantes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor
from ..domain.errors import AuthenticationError, ForbiddenError, NotFoundError
from ..ports.security import TokenService
from .donor_service import DonorService


@dataclass(frozen=True)
class AuthSession:
    token: str
    donor: Donor


REQUEST_AUDIENCE = "request"
# El estado y las alertas se pueden revisar un día después de que vence la solicitud.
REQUEST_TOKEN_GRACE = timedelta(hours=24)


class AuthService:
    def __init__(self, donors: DonorService, tokens: TokenService) -> None:
        self._donors = donors
        self._tokens = tokens

    def login(self, email: str, password: str) -> AuthSession:
        donor = self._donors.authenticate(email, password)
        return AuthSession(self._tokens.issue(donor.id), donor)

    def donor_id_from(self, token: str) -> str:
        donor_id = self._tokens.verify(token)
        try:
            self._donors.get(donor_id)  # el donante del token debe seguir existiendo
        except NotFoundError:
            raise AuthenticationError("Sesión inválida: el donante ya no existe") from None
        return donor_id

    def issue_request_token(self, request: BloodRequest) -> str:
        return self._tokens.issue(request.id, REQUEST_AUDIENCE, request.deadline + REQUEST_TOKEN_GRACE)

    def check_request_token(self, request_id: str, token: str) -> None:
        if self._tokens.verify(token, REQUEST_AUDIENCE) != request_id:
            raise ForbiddenError("Este token es de otra solicitud")
