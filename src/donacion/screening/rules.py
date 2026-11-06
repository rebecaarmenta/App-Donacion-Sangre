"""Reglas de elegibilidad del donante (NOM-253-SSA1-2012).

Cada regla es una clase con una sola responsabilidad. Para agregar una regla nueva
se crea otra clase y se registra en container.py, sin modificar el evaluador.
Los plazos son configurables en el constructor; verificar contra la norma vigente.
"""
from __future__ import annotations

import calendar
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta

from ..domain.donor import Donor
from ..domain.eligibility import EligibilityStatus, ScreeningAnswers


@dataclass(frozen=True)
class RuleOutcome:
    """Resultado de una regla que NO se cumple. Si la regla pasa, se devuelve None."""
    status: EligibilityStatus          # DEFERRED o INELIGIBLE
    reason: str
    eligible_from: date | None = None


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class EligibilityRule(ABC):
    @abstractmethod
    def evaluate(self, donor: Donor, answers: ScreeningAnswers, today: date) -> RuleOutcome | None:
        """Devuelve None si la regla se cumple."""


class AgeRule(EligibilityRule):
    def __init__(self, min_age: int = 18, max_age: int = 65) -> None:
        self._min, self._max = min_age, max_age

    def evaluate(self, donor, answers, today):
        age = donor.age_on(today)
        if age < self._min:
            birthday = add_months(donor.birth_date, self._min * 12)
            return RuleOutcome(EligibilityStatus.DEFERRED,
                               f"Edad mínima {self._min} años (tiene {age})", birthday)
        if age > self._max:
            return RuleOutcome(EligibilityStatus.INELIGIBLE, f"Edad máxima {self._max} años (tiene {age})")
        return None


class WeightRule(EligibilityRule):
    def __init__(self, min_kg: float = 50.0) -> None:
        self._min = min_kg

    def evaluate(self, donor, answers, today):
        if donor.weight_kg < self._min:
            return RuleOutcome(EligibilityStatus.INELIGIBLE, f"Peso mínimo {self._min:g} kg")
        return None


class _WaitingPeriodRule(EligibilityRule):
    """Base para reglas del tipo 'esperar N tiempo desde un evento'."""
    _label = ""

    def _event_date(self, donor: Donor, answers: ScreeningAnswers) -> date | None:
        raise NotImplementedError

    def _until(self, event: date) -> date:
        raise NotImplementedError

    def evaluate(self, donor, answers, today):
        event = self._event_date(donor, answers)
        if event is None:
            return None
        until = self._until(event)
        if today < until:
            return RuleOutcome(EligibilityStatus.DEFERRED, self._label, until)
        return None


class TattooRule(_WaitingPeriodRule):
    _label = "Tatuaje o perforación reciente"

    def __init__(self, months: int = 12) -> None:
        self._months = months

    def _event_date(self, donor, answers): return answers.tattoo_or_piercing_date
    def _until(self, event): return add_months(event, self._months)


class SurgeryRule(_WaitingPeriodRule):
    _label = "Cirugía reciente"

    def __init__(self, months: int = 6) -> None:
        self._months = months

    def _event_date(self, donor, answers): return answers.surgery_date
    def _until(self, event): return add_months(event, self._months)


class MedicationRule(_WaitingPeriodRule):
    _label = "Medicamento reciente"

    def __init__(self, days: int = 5) -> None:
        self._days = days

    def _event_date(self, donor, answers): return answers.medication_end_date
    def _until(self, event): return event + timedelta(days=self._days)


class DonationIntervalRule(_WaitingPeriodRule):
    _label = "Donación reciente"

    def __init__(self, days: int = 56) -> None:
        self._days = days

    @property
    def days(self) -> int:
        return self._days

    def _event_date(self, donor, answers): return donor.last_donation
    def _until(self, event): return event + timedelta(days=self._days)


class PermanentExclusionRule(EligibilityRule):
    def evaluate(self, donor, answers, today):
        if answers.permanent_exclusion:
            return RuleOutcome(EligibilityStatus.INELIGIBLE, "Condición médica que excluye de forma permanente")
        return None
