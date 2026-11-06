"""Resultado del tamizaje y respuestas del cuestionario (value objects)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class EligibilityStatus(str, Enum):
    PENDING = "pendiente"      # aún no contesta el cuestionario
    ELIGIBLE = "apto"
    DEFERRED = "diferido"      # no apto temporalmente, con fecha de regreso
    INELIGIBLE = "no_apto"     # exclusión permanente


@dataclass(frozen=True)
class EligibilityResult:
    status: EligibilityStatus
    reasons: tuple[str, ...] = ()
    eligible_from: date | None = None

    @classmethod
    def pending(cls) -> EligibilityResult:
        return cls(EligibilityStatus.PENDING, ("Falta contestar el cuestionario de tamizaje",))

    def allows_donation_on(self, day: date) -> bool:
        if self.status is EligibilityStatus.ELIGIBLE:
            return True
        if self.status is EligibilityStatus.DEFERRED and self.eligible_from is not None:
            return day >= self.eligible_from
        return False


@dataclass(frozen=True)
class ScreeningAnswers:
    """Respuestas del cuestionario. Edad, peso y última donación salen del perfil."""
    tattoo_or_piercing_date: date | None = None
    surgery_date: date | None = None
    medication_end_date: date | None = None
    permanent_exclusion: bool = False   # p. ej. VIH, hepatitis B/C
    notes: tuple[str, ...] = field(default=())
