"""Caso de uso: el agente reparte las alertas de una solicitud por oleadas.

La primera oleada y la vista previa de candidatos las calcula fast_agent (solo reglas): deben
salir en menos de 5 y 2 segundos (documento de visión, secciones 7 y 9.3) y un modelo local
puede tardar mucho más. Las oleadas
siguientes, que tienen 15 minutos de margen, las planea el agente principal (con IA si está activa).

Concurrencia: la IA puede tardar alrededor de un minuto y mientras tanto otra persona puede
confirmar o adelantar una oleada. Por eso la IA piensa FUERA del candado de escritura y, al
terminar, la oleada vuelve a leer la solicitud: solo se envía si sigue abierta y nadie mandó otra
mientras tanto. Nunca se guarda una copia leída antes de consultar a la IA.
"""
from __future__ import annotations

import logging
import threading

from ..agent.matching_agent import MatchingAgent
from ..domain.alert import Alert, RankedCandidate
from ..ports.alert_log import AlertLog
from ..ports.clock import Clock
from ..ports.notifier import NotificationError, Notifier
from ..ports.repositories import DonorRepository, RequestRepository
from .request_finder import RequestFinder

log = logging.getLogger(__name__)


class MatchingService:
    def __init__(self, agent: MatchingAgent, donors: DonorRepository, requests: RequestRepository,
                 finder: RequestFinder, notifier: Notifier, alert_log: AlertLog, clock: Clock,
                 fast_agent: MatchingAgent | None = None, write_lock: threading.RLock | None = None) -> None:
        self._agent = agent
        self._fast_agent = fast_agent or agent
        # Una sola oleada se planea a la vez (el escalamiento corre en otro hilo que la API).
        self._plan_lock = threading.RLock()
        # Compartido con la fachada: toda lectura-modificación-escritura de datos pasa por aquí.
        self._write_lock = write_lock or threading.RLock()
        self._donors = donors
        self._requests = requests
        self._finder = finder
        self._notifier = notifier
        self._alert_log = alert_log
        self._clock = clock

    def preview(self, request_id: str) -> list[RankedCandidate]:
        """Muestra el orden por reglas sin enviar nada (rápido, sin esperar al modelo de IA)."""
        return self._fast_agent.rank(self._finder.get_open(request_id), self._donors.list_all(), self._clock.now())

    def dispatch(self, request_id: str) -> list[Alert]:
        """Envía la siguiente oleada. Devuelve [] si ya no quedan candidatos, o si mientras la IA
        pensaba la solicitud se cubrió, venció o alguien más mandó otra oleada."""
        with self._plan_lock:
            request = self._finder.get_open(request_id)
            waves_before = request.waves_sent
            agent = self._fast_agent if waves_before == 0 else self._agent
            alerts = agent.plan_wave(request, self._donors.list_all(), self._clock.now())  # puede tardar
            if not alerts:
                return []
            with self._write_lock:
                current = self._finder.get(request_id)   # copia fresca, no la de antes de la IA
                if not current.is_open() or current.waves_sent != waves_before:
                    log.info("Oleada descartada: la solicitud %s cambió mientras el agente pensaba", request_id)
                    return []
                current.register_wave([a.donor_id for a in alerts], self._clock.now())
                for alert in alerts:
                    donor = self._donors.get(alert.donor_id)
                    donor.register_alert()
                    self._donors.save(donor)
                    self._alert_log.record(alert)  # queda visible en la app aunque falle el aviso
                self._requests.save(current)
        for alert in alerts:                    # los reintentos no detienen al resto de la app
            try:
                self._notifier.send(alert)
            except NotificationError as exc:
                log.error("%s", exc)
        return alerts

    def alerts_for_request(self, request_id: str) -> list[Alert]:
        return self._alert_log.for_request(request_id)

    def alerts_for_donor(self, donor_id: str) -> list[Alert]:
        return self._alert_log.for_donor(donor_id)

    def escalate_due(self) -> dict[str, list[Alert]]:
        """Revisa las solicitudes abiertas y envía otra oleada a las que no se cubrieron a tiempo.
        Cada solicitud se vuelve a leer justo antes de decidir: la lista inicial pudo quedar vieja
        mientras la IA pensaba la oleada de otra."""
        sent: dict[str, list[Alert]] = {}
        for request_id in [r.id for r in self._requests.list_open()]:
            with self._plan_lock:
                with self._write_lock:
                    request = self._requests.get(request_id)
                    if request is None or not request.is_open():
                        continue
                    now = self._clock.now()
                    request.expire_if_needed(now)
                    if not request.is_open():
                        self._requests.save(request)   # se marca vencida
                        continue
                    due = request.waves_sent > 0 and self._agent.is_wave_due(request, now)
                if due:
                    alerts = self.dispatch(request_id)
                    if alerts:
                        sent[request_id] = alerts
        return sent
