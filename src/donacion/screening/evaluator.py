"""Evaluador del tamizaje: combina el resultado de todas las reglas."""
from __future__ import annotations

from datetime import date

from ..domain.donor import Donor
from ..domain.eligibility import EligibilityResult, EligibilityStatus, ScreeningAnswers
from .rules import EligibilityRule


class ScreeningEvaluator:
    def __init__(self, rules: list[EligibilityRule]) -> None:
        if not rules:
            raise ValueError("El evaluador necesita al menos una regla")
        self._rules = list(rules)

    def evaluate(self, donor: Donor, answers: ScreeningAnswers, today: date) -> EligibilityResult:
        outcomes = [o for rule in self._rules if (o := rule.evaluate(donor, answers, today)) is not None]
        if not outcomes:
            return EligibilityResult(EligibilityStatus.ELIGIBLE, ("Cumple todos los requisitos",))

        reasons = tuple(o.reason for o in outcomes)
        if any(o.status is EligibilityStatus.INELIGIBLE for o in outcomes):
            return EligibilityResult(EligibilityStatus.INELIGIBLE, reasons)
        # Varios diferimientos: puede donar cuando se cumpla el más lejano.
        eligible_from = max(o.eligible_from for o in outcomes if o.eligible_from)
        return EligibilityResult(EligibilityStatus.DEFERRED, reasons, eligible_from)
