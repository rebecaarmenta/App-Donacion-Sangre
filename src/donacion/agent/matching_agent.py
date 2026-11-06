"""Agente de priorización y matching.

Ciclo de decisión ante una solicitud:
1. Filtra (reglas duras): compatibilidad ABO/Rh y elegibilidad médica.
2. Prioriza (estrategia intercambiable: reglas o IA con respaldo).
3. Planea la oleada: a quién avisar ahora sin repetir donantes.
4. Explica cada alerta.
El agente decide; el servicio persiste los cambios y envía las notificaciones.
"""
from __future__ import annotations

from datetime import datetime

from ..domain.alert import Alert, RankedCandidate
from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor
from .explanation import ExplanationBuilder
from .filters import CandidateFilter
from .scoring import ScoringStrategy
from .waves import WavePlanner


class MatchingAgent:
    def __init__(self, filters: list[CandidateFilter], scoring: ScoringStrategy,
                 planner: WavePlanner, explainer: ExplanationBuilder) -> None:
        self._filters = list(filters)
        self._scoring = scoring
        self._planner = planner
        self._explainer = explainer

    def rank(self, request: BloodRequest, donors: list[Donor], now: datetime) -> list[RankedCandidate]:
        candidates = list(donors)
        for f in self._filters:
            candidates = f.apply(candidates, request, now)
        return self._scoring.rank(candidates, request)

    def is_wave_due(self, request: BloodRequest, now: datetime) -> bool:
        return self._planner.is_due(request, now)

    def plan_wave(self, request: BloodRequest, donors: list[Donor], now: datetime) -> list[Alert]:
        if not request.is_open():
            return []
        wave = self._planner.next_wave(self.rank(request, donors, now), request)
        messages = self._explainer.explain(wave, request)
        number = request.waves_sent + 1
        return [
            Alert(request.id, c.donor.id, c.donor.name, number, c.score, messages[c.donor.id])
            for c in wave
        ]
