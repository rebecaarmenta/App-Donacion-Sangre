"""Revisa periódicamente las solicitudes abiertas y envía la siguiente oleada a las que no se
cubrieron a tiempo (documento de visión, sección 5: "si en 15 minutos no se cubren las unidades,
envía la siguiente oleada"). Corre en un hilo aparte para no bloquear a la API.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)


class EscalationScheduler:
    def __init__(self, check: Callable[[], dict], interval_seconds: float) -> None:
        self._check = check
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="escalamiento", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                sent = self._check()
                for request_id, alerts in sent.items():
                    log.info("Escalamiento: oleada %d enviada para %s", alerts[0].wave, request_id)
            except Exception:  # una falla no debe apagar el escalamiento
                log.exception("Falló la revisión de escalamiento")
