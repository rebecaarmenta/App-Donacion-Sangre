"""Tipo de sangre (value object) y reglas de compatibilidad ABO/Rh para glóbulos rojos."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import ValidationError

# Para cada grupo ABO del receptor: de qué grupos puede recibir.
_ABO_ACCEPTS = {
    "O": frozenset({"O"}),
    "A": frozenset({"A", "O"}),
    "B": frozenset({"B", "O"}),
    "AB": frozenset({"A", "B", "AB", "O"}),
}


@dataclass(frozen=True)
class BloodType:
    abo: str
    rh: str  # "+" o "-"

    def __post_init__(self) -> None:
        if self.abo not in _ABO_ACCEPTS:
            raise ValidationError(f"Grupo ABO inválido: {self.abo!r}")
        if self.rh not in ("+", "-"):
            raise ValidationError(f"Factor Rh inválido: {self.rh!r}")

    @classmethod
    def parse(cls, text: str) -> BloodType:
        """Convierte textos como 'A+', 'ab-' u 'O+' en un BloodType."""
        value = text.strip().upper()
        if len(value) < 2:
            raise ValidationError(f"Tipo de sangre inválido: {text!r}")
        return cls(abo=value[:-1], rh=value[-1])

    def can_donate_to(self, recipient: BloodType) -> bool:
        abo_ok = self.abo in _ABO_ACCEPTS[recipient.abo]
        # Rh- puede donar a cualquiera; Rh+ solo a receptores Rh+.
        rh_ok = self.rh == "-" or recipient.rh == "+"
        return abo_ok and rh_ok

    def is_universal_donor(self) -> bool:
        return self.abo == "O" and self.rh == "-"

    def __str__(self) -> str:
        return f"{self.abo}{self.rh}"
