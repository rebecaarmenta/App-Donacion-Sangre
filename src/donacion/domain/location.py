"""Ubicación geográfica (value object)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import ValidationError

_EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90 <= self.lat <= 90 or not -180 <= self.lon <= 180:
            raise ValidationError("Coordenadas fuera de rango")

    def distance_km(self, other: Location) -> float:
        """Distancia en línea recta (fórmula de Haversine)."""
        lat1, lon1, lat2, lon2 = map(math.radians, (self.lat, self.lon, other.lat, other.lon))
        a = (math.sin((lat2 - lat1) / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
        return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))
