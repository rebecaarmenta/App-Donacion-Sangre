"""Caso de uso: crear solicitudes de sangre y confirmar donaciones."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..domain.blood_request import BloodRequest, Hospital, Urgency
from ..domain.blood_type import BloodType
from ..domain.errors import NotFoundError, ValidationError
from ..domain.location import Location
from ..ports.clock import Clock
from ..ports.ids import IdGenerator
from ..ports.repositories import DonorRepository, RequestRepository


@dataclass(frozen=True)
class CreateRequestCommand:
    requester_name: str
    blood_type: str
    units_needed: int
    hospital_name: str
    hospital_lat: float
    hospital_lon: float
    urgency: str
    deadline: datetime


class RequestService:
    def __init__(self, requests: RequestRepository, donors: DonorRepository, clock: Clock,
                 donation_interval_days: int, ids: IdGenerator) -> None:
        self._requests = requests
        self._donors = donors
        self._clock = clock
        self._interval = timedelta(days=donation_interval_days)
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
            hospital=Hospital(cmd.hospital_name, Location(cmd.hospital_lat, cmd.hospital_lon)),
            urgency=urgency,
            deadline=cmd.deadline,
            created_at=self._clock.now(),
        )
        self._requests.save(request)
        return request

    def get(self, request_id: str) -> BloodRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError(f"No existe la solicitud {request_id}")
        request.expire_if_needed(self._clock.now())
        return request

    def confirm_donation(self, request_id: str, donor_id: str) -> BloodRequest:
        request = self.get(request_id)
        donor = self._donors.get(donor_id)
        if donor is None:
            raise NotFoundError(f"No existe el donante {donor_id}")
        request.confirm_unit(donor_id)
        today = self._clock.now().date()
        donor.record_donation(today, today + self._interval)
        self._requests.save(request)
        self._donors.save(donor)
        return request
