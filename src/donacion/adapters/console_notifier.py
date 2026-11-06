"""Notificador del MVP: escribe la alerta en el log del servidor.
En una versión posterior se sustituye por notificaciones push sin tocar los servicios.
Guardar el historial de alertas es responsabilidad de AlertLog, no de esta clase."""
from __future__ import annotations

import logging

from ..domain.alert import Alert
from ..ports.notifier import Notifier

log = logging.getLogger("donacion.alertas")


class ConsoleNotifier(Notifier):
    def send(self, alert: Alert) -> None:
        log.info("[oleada %d] -> %s: %s", alert.wave, alert.donor_name, alert.message)
