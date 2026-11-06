"""Historial de respuesta del donante (value object inmutable).

Extraído de Donor (refactorización Extract Class): el perfil del donante y sus estadísticas
de respuesta a alertas son responsabilidades distintas.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

# Tasa supuesta para quien todavía no recibe alertas.
DEFAULT_RESPONSE_RATE = 0.5


@dataclass(frozen=True)
class ResponseHistory:
    received: int = 0
    accepted: int = 0

    @property
    def rate(self) -> float:
        if self.received == 0:
            return DEFAULT_RESPONSE_RATE
        return self.accepted / self.received

    def with_alert(self) -> ResponseHistory:
        return replace(self, received=self.received + 1)

    def with_acceptance(self) -> ResponseHistory:
        return replace(self, accepted=self.accepted + 1)
