"""Candidato ordenado por el agente y alerta enviada (value objects)."""
from __future__ import annotations

from dataclasses import dataclass

from .donor import Donor


@dataclass(frozen=True)
class RankedCandidate:
    donor: Donor
    score: float              # 0 a 100
    distance_km: float
    reasons: tuple[str, ...]  # por qué tiene ese puntaje


@dataclass(frozen=True)
class Alert:
    request_id: str
    donor_id: str
    donor_name: str
    wave: int
    score: float
    message: str
