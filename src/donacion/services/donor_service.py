"""Caso de uso: registro, autenticación y perfil del donante."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..domain.blood_type import BloodType
from ..domain.donor import Donor
from ..domain.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from ..domain.location import Location
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


class DonorService:
    def __init__(self, repository: DonorRepository, hasher: PasswordHasher, ids: IdGenerator) -> None:
        self._repository = repository
        self._hasher = hasher
        self._ids = ids

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
