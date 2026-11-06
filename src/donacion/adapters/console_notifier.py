"""Notificador del MVP: escribe la alerta en el log y la guarda en una bandeja consultable.
En una versión posterior se sustituye por notificaciones push sin tocar los servicios."""
from __future__ import annotations

import logging

from ..domain.alert import Alert
from ..ports.notifier import Notifier

log = logging.getLogger("donacion.alertas")


class ConsoleNotifier(Notifier):
    def __init__(self) -> None:
        self._outbox: list[Alert] = []

    def send(self, alert: Alert) -> None:
        self._outbox.append(alert)
        log.info("[oleada %d] -> %s: %s", alert.wave, alert.donor_name, alert.message)

    def sent_to(self, donor_id: str) -> list[Alert]:
        return [a for a in self._outbox if a.donor_id == donor_id]

    def sent_for(self, request_id: str) -> list[Alert]:
        return [a for a in self._outbox if a.request_id == request_id]
