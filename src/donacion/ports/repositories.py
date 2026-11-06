"""Puertos de persistencia. Los servicios dependen de estas interfaces, no de una base de datos."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor


class DonorRepository(ABC):
    @abstractmethod
    def save(self, donor: Donor) -> None: ...

    @abstractmethod
    def get(self, donor_id: str) -> Donor | None: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Donor | None: ...

    @abstractmethod
    def list_all(self) -> list[Donor]: ...


class RequestRepository(ABC):
    @abstractmethod
    def save(self, request: BloodRequest) -> None: ...

    @abstractmethod
    def get(self, request_id: str) -> BloodRequest | None: ...

    @abstractmethod
    def list_open(self) -> list[BloodRequest]: ...
