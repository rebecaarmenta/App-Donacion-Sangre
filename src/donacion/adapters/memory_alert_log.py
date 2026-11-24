"""Registro de alertas en memoria."""
from __future__ import annotations

from ..domain.alert import Alert
from ..ports.alert_log import AlertLog


class InMemoryAlertLog(AlertLog):
    def __init__(self) -> None:
        self._alerts: list[Alert] = []

    def record(self, alert: Alert) -> None:
        self._alerts.append(alert)

    def for_donor(self, donor_id: str) -> list[Alert]:
        return [a for a in self._alerts if a.donor_id == donor_id]

    def for_request(self, request_id: str) -> list[Alert]:
        return [a for a in self._alerts if a.request_id == request_id]
