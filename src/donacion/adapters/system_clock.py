"""Relojes: el real para producción y uno controlable para pruebas y demos."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..ports.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now()


class ManualClock(Clock):
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, minutes: int) -> None:
        self._now += timedelta(minutes=minutes)
