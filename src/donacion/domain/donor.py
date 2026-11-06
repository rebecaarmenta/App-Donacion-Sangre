"""Entidad Donante."""
from __future__ import annotations

from datetime import date

from .blood_type import BloodType
from .eligibility import EligibilityResult, EligibilityStatus
from .errors import ValidationError
from .location import Location
from .response_history import ResponseHistory


class Donor:
    def __init__(self, donor_id: str, name: str, email: str, password_hash: str,
                 birth_date: date, weight_kg: float, blood_type: BloodType,
                 location: Location, last_donation: date | None = None) -> None:
        if not name.strip():
            raise ValidationError("El nombre es obligatorio")
        if "@" not in email:
            raise ValidationError("Correo inválido")
        if weight_kg <= 0:
            raise ValidationError("El peso debe ser positivo")
        self._id = donor_id
        self._name = name.strip()
        self._email = email.strip().lower()
        self._password_hash = password_hash
        self._birth_date = birth_date
        self._weight_kg = weight_kg
        self._blood_type = blood_type
        self._location = location
        self._last_donation = last_donation
        self._eligibility = EligibilityResult.pending()
        self._history = ResponseHistory()

    # ---- lectura ----
    @property
    def id(self) -> str: return self._id
    @property
    def name(self) -> str: return self._name
    @property
    def email(self) -> str: return self._email
    @property
    def password_hash(self) -> str: return self._password_hash
    @property
    def birth_date(self) -> date: return self._birth_date
    @property
    def weight_kg(self) -> float: return self._weight_kg
    @property
    def blood_type(self) -> BloodType: return self._blood_type
    @property
    def location(self) -> Location: return self._location
    @property
    def last_donation(self) -> date | None: return self._last_donation
    @property
    def eligibility(self) -> EligibilityResult: return self._eligibility

    @property
    def response_history(self) -> ResponseHistory: return self._history

    @property
    def response_rate(self) -> float:
        return self._history.rate

    def age_on(self, day: date) -> int:
        years = day.year - self._birth_date.year
        if (day.month, day.day) < (self._birth_date.month, self._birth_date.day):
            years -= 1
        return years

    def can_donate_on(self, day: date) -> bool:
        return self._eligibility.allows_donation_on(day)

    # ---- comportamiento ----
    def update_eligibility(self, result: EligibilityResult) -> None:
        self._eligibility = result

    def register_alert(self) -> None:
        self._history = self._history.with_alert()

    def record_donation(self, day: date, next_eligible: date) -> None:
        """Registra una donación confirmada y difiere al donante hasta next_eligible."""
        self._last_donation = day
        self._history = self._history.with_acceptance()
        self._eligibility = EligibilityResult(
            EligibilityStatus.DEFERRED,
            ("Donó recientemente",),
            next_eligible,
        )
