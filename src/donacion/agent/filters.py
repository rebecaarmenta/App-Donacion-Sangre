"""Filtros de candidatos: deciden quién PUEDE recibir la alerta (reglas duras, sin IA)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor


class CandidateFilter(ABC):
    @abstractmethod
    def apply(self, donors: list[Donor], request: BloodRequest, now: datetime) -> list[Donor]: ...


class CompatibilityFilter(CandidateFilter):
    """Solo donantes con sangre compatible con el paciente (ABO/Rh)."""

    def apply(self, donors, request, now):
        return [d for d in donors if d.blood_type.can_donate_to(request.blood_type)]


class EligibilityFilter(CandidateFilter):
    """Solo donantes aptos hoy según su último tamizaje (descarta pendientes, diferidos y no aptos)."""

    def apply(self, donors, request, now):
        return [d for d in donors if d.can_donate_on(now.date())]


class MaxDistanceFilter(CandidateFilter):
    """Descarta donantes demasiado lejos del hospital."""

    def __init__(self, max_km: float) -> None:
        self._max_km = max_km

    def apply(self, donors, request, now):
        return [d for d in donors if d.location.distance_km(request.hospital.location) <= self._max_km]
