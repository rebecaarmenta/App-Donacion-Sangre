"""Búsqueda de solicitudes compartida por los servicios.

Antes RequestService y MatchingService repetían "buscar, marcar vencida y validar"
(refactorización: eliminar código duplicado / Extract Class).
"""
from __future__ import annotations

from ..domain.blood_request import BloodRequest
from ..domain.errors import ConflictError, NotFoundError
from ..ports.clock import Clock
from ..ports.repositories import RequestRepository


class RequestFinder:
    def __init__(self, requests: RequestRepository, clock: Clock) -> None:
        self._requests = requests
        self._clock = clock

    def get(self, request_id: str) -> BloodRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError(f"No existe la solicitud {request_id}")
        request.expire_if_needed(self._clock.now())
        return request

    def get_open(self, request_id: str) -> BloodRequest:
        request = self.get(request_id)
        if not request.is_open():
            raise ConflictError(f"La solicitud está {request.status.value}")
        return request
