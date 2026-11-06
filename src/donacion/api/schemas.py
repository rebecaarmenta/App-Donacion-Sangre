"""Modelos de entrada y salida de la API (Pydantic). Separan el formato HTTP del dominio."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..domain.alert import Alert, RankedCandidate
from ..domain.blood_request import BloodRequest
from ..domain.donor import Donor
from ..domain.eligibility import EligibilityResult


# ---------- entrada ----------
class DonorIn(BaseModel):
    name: str = Field(min_length=1, examples=["Ana López"])
    email: str = Field(examples=["ana@correo.com"])
    password: str = Field(min_length=8)
    birth_date: date = Field(examples=["2000-05-10"])
    weight_kg: float = Field(gt=0, examples=[62])
    blood_type: str = Field(examples=["O+"])
    lat: float = Field(examples=[20.6736])
    lon: float = Field(examples=[-103.344])
    last_donation: date | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class ScreeningIn(BaseModel):
    tattoo_or_piercing_date: date | None = None
    surgery_date: date | None = None
    medication_end_date: date | None = None
    permanent_exclusion: bool = False


class RequestIn(BaseModel):
    requester_name: str = Field(examples=["Familia Pérez"])
    blood_type: str = Field(examples=["A+"])
    units_needed: int = Field(ge=1, examples=[2])
    hospital_name: str = Field(examples=["Hospital Civil Fray Antonio Alcalde"])
    hospital_lat: float = Field(examples=[20.6866])
    hospital_lon: float = Field(examples=[-103.3496])
    urgency: Literal["critica", "alta", "normal"]
    hours_valid: int = Field(default=24, ge=1, le=168)


class ConfirmIn(BaseModel):
    donor_id: str


# ---------- salida ----------
class EligibilityOut(BaseModel):
    status: str
    reasons: list[str]
    eligible_from: date | None

    @classmethod
    def of(cls, r: EligibilityResult) -> EligibilityOut:
        return cls(status=r.status.value, reasons=list(r.reasons), eligible_from=r.eligible_from)


class DonorOut(BaseModel):
    id: str
    name: str
    email: str
    blood_type: str
    weight_kg: float
    last_donation: date | None
    response_rate: float
    eligibility: EligibilityOut

    @classmethod
    def of(cls, d: Donor) -> DonorOut:
        return cls(id=d.id, name=d.name, email=d.email, blood_type=str(d.blood_type),
                   weight_kg=d.weight_kg, last_donation=d.last_donation,
                   response_rate=round(d.response_rate, 2), eligibility=EligibilityOut.of(d.eligibility))


class RequestOut(BaseModel):
    id: str
    requester_name: str
    blood_type: str
    units_needed: int
    units_confirmed: int
    hospital: str
    urgency: str
    status: str
    deadline: datetime
    waves_sent: int
    notified_donors: list[str]
    confirmed_donors: list[str]

    @classmethod
    def of(cls, r: BloodRequest) -> RequestOut:
        return cls(id=r.id, requester_name=r.requester_name, blood_type=str(r.blood_type),
                   units_needed=r.units_needed, units_confirmed=r.units_confirmed,
                   hospital=r.hospital.name, urgency=r.urgency.value, status=r.status.value,
                   deadline=r.deadline, waves_sent=r.waves_sent,
                   notified_donors=list(r.notified_donors), confirmed_donors=list(r.confirmed_donors))


class CandidateOut(BaseModel):
    position: int
    donor_id: str
    name: str
    blood_type: str
    score: float
    distance_km: float
    reasons: list[str]

    @classmethod
    def of(cls, position: int, c: RankedCandidate) -> CandidateOut:
        return cls(position=position, donor_id=c.donor.id, name=c.donor.name,
                   blood_type=str(c.donor.blood_type), score=c.score,
                   distance_km=c.distance_km, reasons=list(c.reasons))


class AlertOut(BaseModel):
    request_id: str
    donor_id: str
    donor_name: str
    wave: int
    score: float
    message: str

    @classmethod
    def of(cls, a: Alert) -> AlertOut:
        return cls(request_id=a.request_id, donor_id=a.donor_id, donor_name=a.donor_name,
                   wave=a.wave, score=a.score, message=a.message)
