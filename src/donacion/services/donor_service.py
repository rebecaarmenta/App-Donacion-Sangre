"""Caso de uso: registro, autenticación y perfil del donante."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..domain.blood_request import BloodRequest
from ..domain.blood_type import BloodType
from ..domain.donor import Donor
from ..domain.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from ..domain.location import Location
from ..ports.clock import Clock
from ..ports.ids import IdGenerator
from ..ports.repositories import DonorRepository
from ..ports.security import PasswordHasher

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class RegisterDonorCommand:
    name: str
    email: str
    password: str
    birth_date: date
    weight_kg: float
    blood_type: str
    lat: float
    lon: float
    last_donation: date | None = None


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Campos editables del perfil; None = no cambia. Tipo de sangre, nacimiento y correo no se editan."""
    name: str | None = None
    weight_kg: float | None = None
    lat: float | None = None
    lon: float | None = None
    last_donation: date | None = None


class DonorService:
    def __init__(self, repository: DonorRepository, hasher: PasswordHasher, ids: IdGenerator,
                 clock: Clock, donation_interval_days: int) -> None:
        self._repository = repository
        self._hasher = hasher
        self._ids = ids
        self._clock = clock
        self._interval = timedelta(days=donation_interval_days)

    def register(self, cmd: RegisterDonorCommand) -> Donor:
        if len(cmd.password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
        if self._repository.find_by_email(cmd.email):
            raise ConflictError("Ya existe un donante con ese correo")
        donor = Donor(
            donor_id=self._ids.new_id(),
            name=cmd.name,
            email=cmd.email,
            password_hash=self._hasher.hash(cmd.password),
            birth_date=cmd.birth_date,
            weight_kg=cmd.weight_kg,
            blood_type=BloodType.parse(cmd.blood_type),
            location=Location(cmd.lat, cmd.lon),
            last_donation=cmd.last_donation,
        )
        self._repository.save(donor)
        return donor

    def authenticate(self, email: str, password: str) -> Donor:
        donor = self._repository.find_by_email(email)
        if donor is None or not self._hasher.verify(password, donor.password_hash):
            raise AuthenticationError("Correo o contraseña incorrectos")
        return donor

    def get(self, donor_id: str) -> Donor:
        donor = self._repository.get(donor_id)
        if donor is None:
            raise NotFoundError(f"No existe el donante {donor_id}")
        return donor

    def list_all(self) -> list[Donor]:
        return self._repository.list_all()

    def record_donation(self, donor_id: str, request: BloodRequest) -> Donor:
        """Registra que el donante donó hoy para la solicitud, lo agrega a su historial y lo
        difiere hasta que pase el intervalo mínimo."""
        donor = self.get(donor_id)
        today = self._clock.now().date()
        donor.record_donation(today, today + self._interval, request.id, request.hospital.name)
        self._repository.save(donor)
        return donor

    def update_profile(self, donor_id: str, cmd: UpdateProfileCommand) -> Donor:
        donor = self.get(donor_id)
        if (cmd.lat is None) != (cmd.lon is None):
            raise ValidationError("La ubicación necesita latitud y longitud")
        if cmd.last_donation is not None and cmd.last_donation > self._clock.now().date():
            raise ValidationError("La última donación no puede ser una fecha futura")
        location = Location(cmd.lat, cmd.lon) if cmd.lat is not None else None
        donor.update_profile(cmd.name, cmd.weight_kg, location, cmd.last_donation)
        self._repository.save(donor)
        return donor
