"""Caso de uso: el donante contesta el cuestionario de tamizaje."""
from __future__ import annotations

from ..domain.eligibility import EligibilityResult, ScreeningAnswers
from ..domain.errors import NotFoundError
from ..ports.clock import Clock
from ..ports.repositories import DonorRepository
from ..screening.evaluator import ScreeningEvaluator


class ScreeningService:
    def __init__(self, repository: DonorRepository, evaluator: ScreeningEvaluator, clock: Clock) -> None:
        self._repository = repository
        self._evaluator = evaluator
        self._clock = clock

    def submit(self, donor_id: str, answers: ScreeningAnswers) -> EligibilityResult:
        donor = self._repository.get(donor_id)
        if donor is None:
            raise NotFoundError(f"No existe el donante {donor_id}")
        result = self._evaluator.evaluate(donor, answers, self._clock.now().date())
        donor.update_eligibility(result)
        self._repository.save(donor)
        return result
