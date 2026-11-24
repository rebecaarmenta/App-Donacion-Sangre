"""Patrón Facade: una sola entrada simple a todo el sistema.

La API (y la demo en consola) solo conocen DonationPlatform. Detrás hay cuatro servicios,
el agente, los repositorios y el reloj, pero quien la usa no necesita saberlo.
"""
from __future__ import annotations

import threading
from datetime import timedelta

from ..domain.alert import Alert, RankedCandidate
from ..domain.blood_request import BloodRequest
from ..domain.donation import DonationHistory
from ..domain.donor import Donor
from ..domain.eligibility import EligibilityResult, ScreeningAnswers
from ..ports.clock import Clock
from .auth_service import AuthService, AuthSession
from .donor_service import DonorService, RegisterDonorCommand, UpdateProfileCommand
from .history_service import HistoryService
from .hospital_catalog import HospitalCatalog
from .matching_service import MatchingService
from .request_service import CreateRequestCommand, RequestService
from .screening_service import ScreeningService

# Los comandos de entrada forman parte de la interfaz pública de la fachada.
__all__ = ["DonationPlatform", "RegisterDonorCommand", "UpdateProfileCommand", "CreateRequestCommand",
           "AuthSession"]


class DonationPlatform:
    def __init__(self, donors: DonorService, auth: AuthService, screening: ScreeningService,
                 requests: RequestService, history: HistoryService, hospitals: HospitalCatalog,
                 matching: MatchingService,
                 clock: Clock, ai_enabled: bool, ai_provider: str | None = None,
                 write_lock: threading.RLock | None = None) -> None:
        self._donors = donors
        self._auth = auth
        # Compartido con MatchingService: los cambios a los datos no se pisan entre hilos
        # (peticiones de la API y escalamiento automático). Solo se toma en operaciones rápidas.
        self._write_lock = write_lock or threading.RLock()
        self._history = history
        self._hospitals = hospitals
        self._screening = screening
        self._requests = requests
        self._matching = matching
        self._clock = clock
        self._ai_enabled = ai_enabled
        self._ai_provider = ai_provider if ai_enabled else None

    @property
    def ai_enabled(self) -> bool:
        return self._ai_enabled

    @property
    def ai_provider(self) -> str | None:
        return self._ai_provider

    @property
    def clock(self) -> Clock:
        return self._clock

    # ---------- donantes ----------
    def register_donor(self, cmd: RegisterDonorCommand) -> Donor:
        with self._write_lock:
            return self._donors.register(cmd)

    def login(self, email: str, password: str) -> AuthSession:
        return self._auth.login(email, password)

    def donor_id_from_token(self, token: str) -> str:
        return self._auth.donor_id_from(token)

    def get_donor(self, donor_id: str) -> Donor:
        return self._donors.get(donor_id)

    def update_profile(self, donor_id: str, cmd: UpdateProfileCommand) -> Donor:
        with self._write_lock:
            return self._donors.update_profile(donor_id, cmd)

    def list_donors(self) -> list[Donor]:
        return self._donors.list_all()

    def donation_history(self, donor_id: str) -> DonationHistory:
        return self._history.for_donor(donor_id)

    def submit_screening(self, donor_id: str, answers: ScreeningAnswers) -> EligibilityResult:
        with self._write_lock:
            return self._screening.submit(donor_id, answers)

    def alerts_for_donor(self, donor_id: str) -> list[Alert]:
        self._donors.get(donor_id)  # 404 si el donante no existe
        return self._matching.alerts_for_donor(donor_id)

    # ---------- solicitudes ----------
    def list_hospitals(self) -> list[tuple[str, str]]:
        return [(hospital_id, h.name) for hospital_id, h in self._hospitals.list_all()]

    def create_request(self, cmd: CreateRequestCommand) -> BloodRequest:
        """Registra la solicitud y el agente envía de inmediato la primera oleada."""
        with self._write_lock:
            request = self._requests.create(cmd)
        self._matching.dispatch(request.id)   # fuera del candado: la oleada toma los suyos
        return self._requests.get(request.id)

    def create_request_valid_for(self, hours: int, **fields) -> BloodRequest:
        deadline = self._clock.now() + timedelta(hours=hours)
        return self.create_request(CreateRequestCommand(**fields, deadline=deadline))

    def request_token(self, request_id: str) -> str:
        """Token para que quien creó la solicitud la maneje (candidatos, alertas, oleadas)."""
        return self._auth.issue_request_token(self._requests.get(request_id))

    def authorize_request(self, request_id: str, token: str) -> None:
        self._auth.check_request_token(request_id, token)

    def get_request(self, request_id: str) -> BloodRequest:
        return self._requests.get(request_id)

    def confirm_donation(self, request_id: str, donor_id: str) -> BloodRequest:
        """Coordina dos casos de uso: la solicitud cuenta la unidad y el donante queda diferido."""
        with self._write_lock:   # las dos escrituras juntas: ninguna oleada se mete en medio
            self._donors.get(donor_id)  # 404 antes de tocar la solicitud
            request = self._requests.confirm_unit(request_id, donor_id)
            self._donors.record_donation(donor_id, request)
            return request

    # ---------- agente ----------
    def preview_candidates(self, request_id: str) -> list[RankedCandidate]:
        return self._matching.preview(request_id)

    def alerts_for_request(self, request_id: str) -> list[Alert]:
        self._requests.get(request_id)  # 404 si la solicitud no existe
        return self._matching.alerts_for_request(request_id)

    def dispatch_wave(self, request_id: str) -> list[Alert]:
        return self._matching.dispatch(request_id)

    def escalate(self) -> dict[str, list[Alert]]:
        return self._matching.escalate_due()
