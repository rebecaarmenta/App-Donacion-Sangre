"""Endpoints HTTP. Solo traducen HTTP <-> servicios; no contienen reglas de negocio."""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request

from ..container import Container
from ..domain.eligibility import ScreeningAnswers
from ..services.donor_service import RegisterDonorCommand
from ..services.request_service import CreateRequestCommand
from .schemas import (AlertOut, CandidateOut, ConfirmIn, DonorIn, DonorOut, EligibilityOut, LoginIn,
                      RequestIn, RequestOut, ScreeningIn)

router = APIRouter()


def get_container(request: Request) -> Container:
    return request.app.state.container


@router.get("/health", tags=["sistema"])
def health(c: Container = Depends(get_container)) -> dict:
    return {"status": "ok", "agente_con_ia": c.llm_enabled}


# ---------- 1. Registro y perfil del donante ----------
@router.post("/donors", response_model=DonorOut, status_code=201, tags=["donantes"])
def register_donor(body: DonorIn, c: Container = Depends(get_container)):
    return DonorOut.of(c.donors.register(RegisterDonorCommand(**body.model_dump())))


@router.post("/auth/login", response_model=DonorOut, tags=["donantes"])
def login(body: LoginIn, c: Container = Depends(get_container)):
    return DonorOut.of(c.donors.authenticate(body.email, body.password))


@router.get("/donors", response_model=list[DonorOut], tags=["donantes"])
def list_donors(c: Container = Depends(get_container)):
    return [DonorOut.of(d) for d in c.donors.list_all()]


@router.get("/donors/{donor_id}", response_model=DonorOut, tags=["donantes"])
def get_donor(donor_id: str, c: Container = Depends(get_container)):
    return DonorOut.of(c.donors.get(donor_id))


@router.get("/donors/{donor_id}/alerts", response_model=list[AlertOut], tags=["donantes"])
def donor_alerts(donor_id: str, c: Container = Depends(get_container)):
    c.donors.get(donor_id)
    return [AlertOut.of(a) for a in c.notifier.sent_to(donor_id)]


# ---------- 2. Cuestionario de tamizaje ----------
@router.post("/donors/{donor_id}/screening", response_model=EligibilityOut, tags=["tamizaje"])
def submit_screening(donor_id: str, body: ScreeningIn, c: Container = Depends(get_container)):
    return EligibilityOut.of(c.screening.submit(donor_id, ScreeningAnswers(**body.model_dump())))


# ---------- 3. Solicitudes de sangre ----------
@router.post("/requests", response_model=RequestOut, status_code=201, tags=["solicitudes"])
def create_request(body: RequestIn, c: Container = Depends(get_container)):
    data = body.model_dump(exclude={"hours_valid"})
    deadline = c.clock.now() + timedelta(hours=body.hours_valid)
    return RequestOut.of(c.requests.create(CreateRequestCommand(**data, deadline=deadline)))


@router.get("/requests/{request_id}", response_model=RequestOut, tags=["solicitudes"])
def get_request(request_id: str, c: Container = Depends(get_container)):
    return RequestOut.of(c.requests.get(request_id))


@router.post("/requests/{request_id}/confirm", response_model=RequestOut, tags=["solicitudes"])
def confirm_donation(request_id: str, body: ConfirmIn, c: Container = Depends(get_container)):
    return RequestOut.of(c.requests.confirm_donation(request_id, body.donor_id))


# ---------- 4. Agente de priorización y matching ----------
@router.get("/requests/{request_id}/candidates", response_model=list[CandidateOut], tags=["agente"])
def preview_candidates(request_id: str, c: Container = Depends(get_container)):
    return [CandidateOut.of(i, cand) for i, cand in enumerate(c.matching.preview(request_id), start=1)]


@router.post("/requests/{request_id}/dispatch", response_model=list[AlertOut], tags=["agente"])
def dispatch_wave(request_id: str, c: Container = Depends(get_container)):
    return [AlertOut.of(a) for a in c.matching.dispatch(request_id)]


@router.post("/requests/escalate", response_model=dict[str, list[AlertOut]], tags=["agente"])
def escalate(c: Container = Depends(get_container)):
    return {rid: [AlertOut.of(a) for a in alerts] for rid, alerts in c.matching.escalate_due().items()}
