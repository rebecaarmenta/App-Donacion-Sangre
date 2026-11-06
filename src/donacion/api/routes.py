"""Endpoints HTTP. Solo traducen HTTP <-> fachada DonationPlatform; no contienen reglas de negocio."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..domain.eligibility import ScreeningAnswers
from ..services.platform import DonationPlatform, RegisterDonorCommand
from .schemas import (AlertOut, CandidateOut, ConfirmIn, DonorIn, DonorOut, EligibilityOut, LoginIn,
                      RequestIn, RequestOut, ScreeningIn)

router = APIRouter()


def get_platform(request: Request) -> DonationPlatform:
    return request.app.state.platform


@router.get("/health", tags=["sistema"])
def health(p: DonationPlatform = Depends(get_platform)) -> dict:
    return {"status": "ok", "agente_con_ia": p.ai_enabled}


# ---------- 1. Registro y perfil del donante ----------
@router.post("/donors", response_model=DonorOut, status_code=201, tags=["donantes"])
def register_donor(body: DonorIn, p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.register_donor(RegisterDonorCommand(**body.model_dump())))


@router.post("/auth/login", response_model=DonorOut, tags=["donantes"])
def login(body: LoginIn, p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.login(body.email, body.password))


@router.get("/donors", response_model=list[DonorOut], tags=["donantes"])
def list_donors(p: DonationPlatform = Depends(get_platform)):
    return [DonorOut.of(d) for d in p.list_donors()]


@router.get("/donors/{donor_id}", response_model=DonorOut, tags=["donantes"])
def get_donor(donor_id: str, p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.get_donor(donor_id))


@router.get("/donors/{donor_id}/alerts", response_model=list[AlertOut], tags=["donantes"])
def donor_alerts(donor_id: str, p: DonationPlatform = Depends(get_platform)):
    return [AlertOut.of(a) for a in p.alerts_for_donor(donor_id)]


# ---------- 2. Cuestionario de tamizaje ----------
@router.post("/donors/{donor_id}/screening", response_model=EligibilityOut, tags=["tamizaje"])
def submit_screening(donor_id: str, body: ScreeningIn, p: DonationPlatform = Depends(get_platform)):
    return EligibilityOut.of(p.submit_screening(donor_id, ScreeningAnswers(**body.model_dump())))


# ---------- 3. Solicitudes de sangre ----------
@router.post("/requests", response_model=RequestOut, status_code=201, tags=["solicitudes"])
def create_request(body: RequestIn, p: DonationPlatform = Depends(get_platform)):
    fields = body.model_dump(exclude={"hours_valid"})
    return RequestOut.of(p.create_request_valid_for(body.hours_valid, **fields))


@router.get("/requests/{request_id}", response_model=RequestOut, tags=["solicitudes"])
def get_request(request_id: str, p: DonationPlatform = Depends(get_platform)):
    return RequestOut.of(p.get_request(request_id))


@router.post("/requests/{request_id}/confirm", response_model=RequestOut, tags=["solicitudes"])
def confirm_donation(request_id: str, body: ConfirmIn, p: DonationPlatform = Depends(get_platform)):
    return RequestOut.of(p.confirm_donation(request_id, body.donor_id))


# ---------- 4. Agente de priorización y matching ----------
@router.get("/requests/{request_id}/candidates", response_model=list[CandidateOut], tags=["agente"])
def preview_candidates(request_id: str, p: DonationPlatform = Depends(get_platform)):
    return [CandidateOut.of(i, c) for i, c in enumerate(p.preview_candidates(request_id), start=1)]


@router.post("/requests/{request_id}/dispatch", response_model=list[AlertOut], tags=["agente"])
def dispatch_wave(request_id: str, p: DonationPlatform = Depends(get_platform)):
    return [AlertOut.of(a) for a in p.dispatch_wave(request_id)]


@router.post("/requests/escalate", response_model=dict[str, list[AlertOut]], tags=["agente"])
def escalate(p: DonationPlatform = Depends(get_platform)):
    return {rid: [AlertOut.of(a) for a in alerts] for rid, alerts in p.escalate().items()}
