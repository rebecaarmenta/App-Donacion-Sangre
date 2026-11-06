"""Patrón Facade: una sola entrada simple a todo el sistema.

La API (y la demo en consola) solo conocen DonationPlatform. Detrás hay cuatro servicios,
el agente, los repositorios y el reloj, pero quien la usa no necesita saberlo.
"""
from __future__ import annotations

from datetime import timedelta

from ..domain.alert import Alert, RankedCandidate
from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor
from ..domain.eligibility import EligibilityResult, ScreeningAnswers
from ..ports.clock import Clock
from .donor_service import DonorService, RegisterDonorCommand
from .matching_service import MatchingService
from .request_service import CreateRequestCommand, RequestService
from .screening_service import ScreeningService


class DonationPlatform:
    def __init__(self, donors: DonorService, screening: ScreeningService, requests: RequestService,
                 matching: MatchingService, clock: Clock, ai_enabled: bool) -> None:
        self._donors = donors
        self._screening = screening
        self._requests = requests
        self._matching = matching
        self._clock = clock
        self._ai_enabled = ai_enabled

    @property
    def ai_enabled(self) -> bool:
        return self._ai_enabled

    @property
    def clock(self) -> Clock:
        return self._clock

    # ---------- donantes ----------
    def register_donor(self, cmd: RegisterDonorCommand) -> Donor:
        return self._donors.register(cmd)

    def login(self, email: str, password: str) -> Donor:
        return self._donors.authenticate(email, password)

    def get_donor(self, donor_id: str) -> Donor:
        return self._donors.get(donor_id)

    def list_donors(self) -> list[Donor]:
        return self._donors.list_all()

    def submit_screening(self, donor_id: str, answers: ScreeningAnswers) -> EligibilityResult:
        return self._screening.submit(donor_id, answers)

    def alerts_for_donor(self, donor_id: str) -> list[Alert]:
        self._donors.get(donor_id)  # 404 si el donante no existe
        return self._matching.alerts_for_donor(donor_id)

    # ---------- solicitudes ----------
    def create_request(self, cmd: CreateRequestCommand) -> BloodRequest:
        return self._requests.create(cmd)

    def create_request_valid_for(self, hours: int, **fields) -> BloodRequest:
        deadline = self._clock.now() + timedelta(hours=hours)
        return self._requests.create(CreateRequestCommand(**fields, deadline=deadline))

    def get_request(self, request_id: str) -> BloodRequest:
        return self._requests.get(request_id)

    def confirm_donation(self, request_id: str, donor_id: str) -> BloodRequest:
        return self._requests.confirm_donation(request_id, donor_id)

    # ---------- agente ----------
    def preview_candidates(self, request_id: str) -> list[RankedCandidate]:
        return self._matching.preview(request_id)

    def dispatch_wave(self, request_id: str) -> list[Alert]:
        return self._matching.dispatch(request_id)

    def escalate(self) -> dict[str, list[Alert]]:
        return self._matching.escalate_due()
