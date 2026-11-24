"""Puerto de notificaciones (push, correo, consola…)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.alert import Alert


class Notifier(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> None: ...


class NotificationError(Exception):
    """No se pudo entregar la alerta (después de los reintentos)."""
