"""Pesos del puntaje del agente (parameter object).

Antes eran números mágicos dentro de RuleBasedScoring (refactorización Introduce Parameter Object).
Ahora se ajustan en un solo lugar sin modificar la estrategia.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringWeights:
    proximity: float = 45.0                  # puntos máximos por cercanía al hospital
    blood_match: float = 25.0                # puntos por compatibilidad de sangre
    compatible_factor: float = 0.6           # fracción de blood_match si no es el mismo tipo
    response: float = 30.0                   # puntos máximos por tasa de respuesta
    universal_reserve_penalty: float = 20.0  # castigo a O- cuando no hace falta
    reference_km: float = 30.0               # a esta distancia la cercanía vale 0
