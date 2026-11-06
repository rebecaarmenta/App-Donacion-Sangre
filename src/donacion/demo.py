"""Datos de prueba para la demo (donantes ficticios en la zona metropolitana de Guadalajara)."""
from __future__ import annotations

from datetime import date, timedelta

from .container import Container
from .domain.eligibility import ScreeningAnswers
from .services.donor_service import RegisterDonorCommand

DEMO_PASSWORD = "demo1234"

# nombre, tipo, nacimiento, peso, lat, lon, días desde última donación, respuestas del tamizaje
_DONORS = [
    ("Ana López", "A+", date(1998, 3, 14), 62, 20.6767, -103.3475, None, {}),
    ("Bruno Díaz", "A-", date(1990, 7, 2), 80, 20.6597, -103.3496, 200, {}),
    ("Carla Ruiz", "O+", date(2001, 11, 21), 55, 20.7020, -103.3880, None, {}),
    ("Diego Mora", "O-", date(1985, 1, 9), 90, 20.6900, -103.3500, 120, {}),
    ("Elena Soto", "A+", date(1995, 6, 30), 58, 20.6200, -103.4200, None, {}),
    ("Fernando Gil", "B+", date(1993, 9, 15), 75, 20.6800, -103.3600, None, {}),
    ("Gabriela Paz", "A+", date(2000, 2, 1), 60, 20.6880, -103.3510, None,
     {"tattoo_or_piercing_date": -90}),                       # tatuaje hace 3 meses -> diferida
    ("Héctor Luna", "O+", date(1988, 4, 18), 82, 20.7300, -103.4000, 30, {}),  # donó hace 30 días -> diferido
    ("Irene Vega", "AB+", date(1997, 12, 5), 64, 20.6750, -103.3450, None, {}),
    ("Jorge Ríos", "A+", date(1979, 8, 22), 48, 20.6850, -103.3480, None, {}),  # peso < 50 -> no apto
    ("Karla Núñez", "O+", date(1999, 5, 11), 57, 20.5800, -103.4500, None, {}),
    ("Luis Ortega", "A-", date(1992, 10, 3), 70, 20.6950, -103.3300, 400, {}),
]


def seed_demo(container: Container) -> None:
    today = container.clock.now().date()
    for i, (name, blood, birth, weight, lat, lon, days_since, answers) in enumerate(_DONORS, start=1):
        last = today - timedelta(days=days_since) if days_since else None
        donor = container.donors.register(RegisterDonorCommand(
            name=name, email=f"donante{i}@demo.mx", password=DEMO_PASSWORD, birth_date=birth,
            weight_kg=weight, blood_type=blood, lat=lat, lon=lon, last_donation=last,
        ))
        dates = {k: today + timedelta(days=v) for k, v in answers.items()}
        container.screening.submit(donor.id, ScreeningAnswers(**dates))
