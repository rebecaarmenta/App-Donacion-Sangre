"""Planificador de oleadas: a cuántos avisar y cuándo pasar a la siguiente oleada."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..domain.alert import RankedCandidate
from ..domain.blood_request import BloodRequest


class WavePlanner:
    def __init__(self, wave_size: int = 10, wait_minutes: float = 15) -> None:
        if wave_size < 1 or wait_minutes < 0:
            raise ValueError("Tamaño de oleada o espera inválidos")
        self._wave_size = wave_size
        self._wait = timedelta(minutes=wait_minutes)

    def is_due(self, request: BloodRequest, now: datetime) -> bool:
        """¿Toca enviar otra oleada? Solo si sigue abierta y ya pasó el tiempo de espera."""
        if not request.is_open():
            return False
        if request.last_wave_at is None:
            return True
        return now - request.last_wave_at >= self._wait

    def next_wave(self, ranked: list[RankedCandidate], request: BloodRequest) -> list[RankedCandidate]:
        already = set(request.notified_donors)
        return [c for c in ranked if c.donor.id not in already][: self._wave_size]
