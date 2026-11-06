"""Repositorios en memoria para el MVP. Para usar una base de datos real basta con
crear otra clase que implemente el mismo puerto y cambiarla en container.py."""
from __future__ import annotations

from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor
from ..ports.repositories import DonorRepository, RequestRepository


class InMemoryDonorRepository(DonorRepository):
    def __init__(self) -> None:
        self._items: dict[str, Donor] = {}

    def save(self, donor: Donor) -> None:
        self._items[donor.id] = donor

    def get(self, donor_id: str) -> Donor | None:
        return self._items.get(donor_id)

    def find_by_email(self, email: str) -> Donor | None:
        email = email.strip().lower()
        return next((d for d in self._items.values() if d.email == email), None)

    def list_all(self) -> list[Donor]:
        return list(self._items.values())


class InMemoryRequestRepository(RequestRepository):
    def __init__(self) -> None:
        self._items: dict[str, BloodRequest] = {}

    def save(self, request: BloodRequest) -> None:
        self._items[request.id] = request

    def get(self, request_id: str) -> BloodRequest | None:
        return self._items.get(request_id)

    def list_open(self) -> list[BloodRequest]:
        return [r for r in self._items.values() if r.is_open()]
