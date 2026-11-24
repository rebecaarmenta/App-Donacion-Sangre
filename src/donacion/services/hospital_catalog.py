"""Catálogo de hospitales autorizados.

La solicitud solo indica el id del hospital. El nombre que se muestra a los donantes y que
llega al modelo de IA sale de aquí, nunca del texto que escribe quien crea la solicitud:
así nadie puede colar instrucciones en las alertas (prompt injection).
"""
from __future__ import annotations

from ..domain.blood_request import Hospital
from ..domain.errors import ValidationError
from ..domain.location import Location


class HospitalCatalog:
    def __init__(self, hospitals: dict[str, Hospital]) -> None:
        self._hospitals = dict(hospitals)

    def get(self, hospital_id: str) -> Hospital:
        hospital = self._hospitals.get(hospital_id)
        if hospital is None:
            raise ValidationError("Hospital desconocido: elige uno del catálogo")
        return hospital

    def list_all(self) -> list[tuple[str, Hospital]]:
        return list(self._hospitals.items())


GUADALAJARA_HOSPITALS = {
    "hc-fray-antonio": Hospital("Hospital Civil Fray Antonio Alcalde", Location(20.6866, -103.3496)),
    "hc-juan-menchaca": Hospital("Hospital Civil Juan I. Menchaca", Location(20.6981, -103.3324)),
    "cmno": Hospital("Centro Médico Nacional de Occidente", Location(20.6835, -103.3266)),
    "cets": Hospital("Centro Estatal de la Transfusión Sanguínea", Location(20.6731, -103.3600)),
}
