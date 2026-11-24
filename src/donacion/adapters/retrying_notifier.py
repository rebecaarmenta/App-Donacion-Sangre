"""Decorador de Notifier: reintenta el envío con espera creciente (documento de visión, sección 7).

Envuelve a cualquier notificador (consola hoy, push mañana) sin que cambie. Si tras todos los
intentos no se pudo enviar, lanza NotificationError para que el servicio lo registre.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from ..domain.alert import Alert
from ..ports.notifier import NotificationError, Notifier

log = logging.getLogger(__name__)


class RetryingNotifier(Notifier):
    def __init__(self, inner: Notifier, attempts: int = 3, delay_seconds: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if attempts < 1:
            raise ValueError("Se necesita al menos un intento")
        self._inner = inner
        self._attempts = attempts
        self._delay = delay_seconds
        self._sleep = sleep

    def send(self, alert: Alert) -> None:
        for attempt in range(1, self._attempts + 1):
            try:
                self._inner.send(alert)
                return
            except Exception as exc:  # cualquier falla del canal cuenta como intento fallido
                if attempt == self._attempts:
                    raise NotificationError(
                        f"No se pudo avisar a {alert.donor_id} tras {attempt} intentos: {exc}") from exc
                log.warning("Falló el aviso a %s (intento %d/%d): %s", alert.donor_id, attempt,
                            self._attempts, exc)
                self._sleep(self._delay * attempt)
