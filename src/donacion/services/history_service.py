"""Caso de uso: el historial de donaciones del donante y su impacto."""
from __future__ import annotations

from ..domain.blood_request import RequestStatus
from ..domain.donation import DonationHistory
from ..ports.repositories import RequestRepository
from .donor_service import DonorService


class HistoryService:
    def __init__(self, donors: DonorService, requests: RequestRepository) -> None:
        self._donors = donors
        self._requests = requests

    def for_donor(self, donor_id: str) -> DonationHistory:
        records = self._donors.get(donor_id).donations
        covered = frozenset(
            r.request_id for r in records
            if r.request_id and (req := self._requests.get(r.request_id)) and req.status is RequestStatus.COVERED)
        return DonationHistory(records, covered)
