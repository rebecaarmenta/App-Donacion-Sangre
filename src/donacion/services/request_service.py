"""Caso de uso: crear solicitudes de sangre y confirmar donaciones."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.blood_request import BloodRequest, Urgency
from ..domain.blood_type import BloodType
from ..domain.errors import ValidationError
from ..ports.clock import Clock
from ..ports.ids import IdGenerator
from ..ports.repositories import RequestRepository
from .hospital_catalog import HospitalCatalog
from .request_finder import RequestFinder


@dataclass(frozen=True)
class CreateRequestCommand:
    requester_name: str
    blood_type: str
    units_needed: int
    hospital_id: str
    urgency: str
    deadline: datetime


class RequestService:
    def __init__(self, requests: RequestRepository, finder: RequestFinder, hospitals: HospitalCatalog,
                 clock: Clock, ids: IdGenerator) -> None:
        self._requests = requests
        self._finder = finder
        self._hospitals = hospitals
        self._clock = clock
        self._ids = ids

    def create(self, cmd: CreateRequestCommand) -> BloodRequest:
        try:
            urgency = Urgency(cmd.urgency.lower())
        except ValueError as exc:
            raise ValidationError("Urgencia inválida: use critica, alta o normal") from exc
        request = BloodRequest(
            request_id=self._ids.new_id(),
            requester_name=cmd.requester_name,
            blood_type=BloodType.parse(cmd.blood_type),
            units_needed=cmd.units_needed,
            hospital=self._hospitals.get(cmd.hospital_id),
            urgency=urgency,
            deadline=cmd.deadline,
            created_at=self._clock.now(),
        )
        self._requests.save(request)
        return request

    def get(self, request_id: str) -> BloodRequest:
        return self._finder.get(request_id)

    def confirm_unit(self, request_id: str, donor_id: str) -> BloodRequest:
        """Solo cuenta la unidad en la solicitud; lo que le pasa al donante lo decide DonorService."""
        request = self.get(request_id)
        request.confirm_unit(donor_id)
        self._requests.save(request)
        return request
