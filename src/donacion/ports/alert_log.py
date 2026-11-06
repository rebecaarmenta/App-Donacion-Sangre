"""Puerto del registro de alertas enviadas.

Separado del Notifier: enviar una alerta y recordarla son responsabilidades distintas (SRP),
y la API consulta este puerto en lugar de un notificador concreto (DIP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.alert import Alert


class AlertLog(ABC):
    @abstractmethod
    def record(self, alert: Alert) -> None: ...

    @abstractmethod
    def for_donor(self, donor_id: str) -> list[Alert]: ...

    @abstractmethod
    def for_request(self, request_id: str) -> list[Alert]: ...
