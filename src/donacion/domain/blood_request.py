"""Entidad Solicitud de sangre y sus tipos asociados."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .blood_type import BloodType
from .errors import ConflictError, ValidationError
from .location import Location


class Urgency(str, Enum):
    CRITICAL = "critica"
    HIGH = "alta"
    NORMAL = "normal"

    @property
    def label(self) -> str:
        return {"critica": "crítica", "alta": "alta", "normal": "normal"}[self.value]


class RequestStatus(str, Enum):
    OPEN = "abierta"
    COVERED = "cubierta"
    EXPIRED = "vencida"


@dataclass(frozen=True)
class Hospital:
    name: str
    location: Location


class BloodRequest:
    def __init__(self, request_id: str, requester_name: str, blood_type: BloodType,
                 units_needed: int, hospital: Hospital, urgency: Urgency,
                 deadline: datetime, created_at: datetime) -> None:
        if units_needed < 1:
            raise ValidationError("Se necesita al menos una unidad")
        if deadline <= created_at:
            raise ValidationError("La fecha límite debe ser posterior a la creación")
        self._id = request_id
        self._requester_name = requester_name
        self._blood_type = blood_type
        self._units_needed = units_needed
        self._hospital = hospital
        self._urgency = urgency
        self._deadline = deadline
        self._created_at = created_at
        self._status = RequestStatus.OPEN
        self._confirmed_donors: list[str] = []
        self._notified_donors: list[str] = []
        self._waves_sent = 0
        self._last_wave_at: datetime | None = None

    @classmethod
    def restore(cls, request_id: str, requester_name: str, blood_type: BloodType, units_needed: int,
                hospital: Hospital, urgency: Urgency, deadline: datetime, created_at: datetime,
                status: RequestStatus, notified_donors: tuple[str, ...], confirmed_donors: tuple[str, ...],
                waves_sent: int, last_wave_at: datetime | None) -> BloodRequest:
        """Reconstruye una solicitud guardada (lo usan los repositorios), con todo su estado."""
        request = cls(request_id, requester_name, blood_type, units_needed, hospital, urgency,
                      deadline, created_at)
        request._status = status
        request._notified_donors = list(notified_donors)
        request._confirmed_donors = list(confirmed_donors)
        request._waves_sent = waves_sent
        request._last_wave_at = last_wave_at
        return request

    # ---- lectura ----
    @property
    def id(self) -> str: return self._id
    @property
    def requester_name(self) -> str: return self._requester_name
    @property
    def blood_type(self) -> BloodType: return self._blood_type
    @property
    def units_needed(self) -> int: return self._units_needed
    @property
    def units_confirmed(self) -> int: return len(self._confirmed_donors)
    @property
    def hospital(self) -> Hospital: return self._hospital
    @property
    def urgency(self) -> Urgency: return self._urgency
    @property
    def deadline(self) -> datetime: return self._deadline
    @property
    def created_at(self) -> datetime: return self._created_at
    @property
    def status(self) -> RequestStatus: return self._status
    @property
    def notified_donors(self) -> tuple[str, ...]: return tuple(self._notified_donors)
    @property
    def confirmed_donors(self) -> tuple[str, ...]: return tuple(self._confirmed_donors)
    @property
    def waves_sent(self) -> int: return self._waves_sent
    @property
    def last_wave_at(self) -> datetime | None: return self._last_wave_at

    def is_open(self) -> bool:
        return self._status is RequestStatus.OPEN

    # ---- comportamiento ----
    def expire_if_needed(self, now: datetime) -> None:
        if self.is_open() and now >= self._deadline:
            self._status = RequestStatus.EXPIRED

    def register_wave(self, donor_ids: list[str], now: datetime) -> None:
        if not self.is_open():
            raise ConflictError("La solicitud ya no está abierta")
        self._notified_donors.extend(d for d in donor_ids if d not in self._notified_donors)
        self._waves_sent += 1
        self._last_wave_at = now

    def confirm_unit(self, donor_id: str) -> None:
        if not self.is_open():
            raise ConflictError("La solicitud ya no está abierta")
        if donor_id not in self._notified_donors:
            raise ConflictError("Solo puede confirmar un donante que recibió la alerta")
        if donor_id in self._confirmed_donors:
            raise ConflictError("Este donante ya confirmó")
        self._confirmed_donors.append(donor_id)
        if self.units_confirmed >= self._units_needed:
            self._status = RequestStatus.COVERED
