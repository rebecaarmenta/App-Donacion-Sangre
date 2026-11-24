"""Historial de donaciones del donante (value objects).

Documento de visión, sección 5, punto 6: "registro de las donaciones de cada usuario y del
impacto generado". El impacto se mide en donaciones hechas y solicitudes que ayudó a cubrir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DonationRecord:
    day: date
    request_id: str | None   # None si la donación no vino de una solicitud de la app
    hospital: str | None


@dataclass(frozen=True)
class DonationHistory:
    records: tuple[DonationRecord, ...]
    covered_request_ids: frozenset[str]   # solicitudes de este historial que ya quedaron cubiertas

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def requests_covered(self) -> int:
        return sum(1 for r in self.records if r.request_id in self.covered_request_ids)

    def newest_first(self) -> list[DonationRecord]:
        return sorted(self.records, key=lambda r: r.day, reverse=True)
