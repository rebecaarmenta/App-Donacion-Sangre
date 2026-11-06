"""Caso de uso: el agente reparte las alertas de una solicitud por oleadas."""
from __future__ import annotations

from ..agent.matching_agent import MatchingAgent
from ..domain.alert import Alert, RankedCandidate
from ..ports.alert_log import AlertLog
from ..ports.clock import Clock
from ..ports.notifier import Notifier
from ..ports.repositories import DonorRepository, RequestRepository
from .request_finder import RequestFinder


class MatchingService:
    def __init__(self, agent: MatchingAgent, donors: DonorRepository, requests: RequestRepository,
                 finder: RequestFinder, notifier: Notifier, alert_log: AlertLog, clock: Clock) -> None:
        self._agent = agent
        self._donors = donors
        self._requests = requests
        self._finder = finder
        self._notifier = notifier
        self._alert_log = alert_log
        self._clock = clock

    def preview(self, request_id: str) -> list[RankedCandidate]:
        """Muestra el orden del agente sin enviar nada (útil para la demo)."""
        return self._agent.rank(self._finder.get_open(request_id), self._donors.list_all(), self._clock.now())

    def dispatch(self, request_id: str) -> list[Alert]:
        """Envía la siguiente oleada. Devuelve [] si ya no quedan candidatos."""
        request = self._finder.get_open(request_id)
        now = self._clock.now()
        alerts = self._agent.plan_wave(request, self._donors.list_all(), now)
        if not alerts:
            return []
        request.register_wave([a.donor_id for a in alerts], now)
        for alert in alerts:
            donor = self._donors.get(alert.donor_id)
            donor.register_alert()
            self._donors.save(donor)
            self._notifier.send(alert)
            self._alert_log.record(alert)
        self._requests.save(request)
        return alerts

    def alerts_for_donor(self, donor_id: str) -> list[Alert]:
        return self._alert_log.for_donor(donor_id)

    def escalate_due(self) -> dict[str, list[Alert]]:
        """Revisa las solicitudes abiertas y envía otra oleada a las que no se cubrieron a tiempo."""
        now = self._clock.now()
        sent: dict[str, list[Alert]] = {}
        for request in self._requests.list_open():
            request.expire_if_needed(now)
            self._requests.save(request)
            if request.waves_sent > 0 and self._agent.is_wave_due(request, now):
                alerts = self.dispatch(request.id)
                if alerts:
                    sent[request.id] = alerts
        return sent
