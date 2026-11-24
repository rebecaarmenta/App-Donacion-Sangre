"""Endpoints HTTP. Solo traducen HTTP <-> fachada DonationPlatform; no contienen reglas de negocio.

Las rutas del donante (/me...) toman su id del token firmado que entrega /auth/login,
nunca del cuerpo ni de la URL: así nadie puede actuar ni leer datos a nombre de otro.
Las rutas que manejan una solicitud (candidatos, alertas, oleadas) piden el token que se
entrega al crearla, en el encabezado X-Request-Token.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from ..domain.eligibility import ScreeningAnswers
from ..domain.errors import AuthenticationError
from ..services.platform import DonationPlatform, RegisterDonorCommand, UpdateProfileCommand
from .schemas import (AlertOut, CandidateOut, CreatedRequestOut, DonationHistoryOut, DonorIn, DonorOut,
                      EligibilityOut, HospitalOut, LoginIn, ProfileUpdateIn, RequestIn, RequestOut, ScreeningIn,
                      SessionOut)

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)
_request_token = APIKeyHeader(name="X-Request-Token", auto_error=False)


def get_platform(request: Request) -> DonationPlatform:
    return request.app.state.platform


def current_donor_id(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     p: DonationPlatform = Depends(get_platform)) -> str:
    if credentials is None:
        raise AuthenticationError("Inicia sesión para continuar")
    return p.donor_id_from_token(credentials.credentials)


def request_owner(request_id: str, token: str | None = Depends(_request_token),
                  p: DonationPlatform = Depends(get_platform)) -> str:
    """Solo quien creó la solicitud (tiene su token) puede manejarla."""
    p.get_request(request_id)  # 404 si no existe
    if not token:
        raise AuthenticationError("Falta el token de la solicitud (X-Request-Token)")
    p.authorize_request(request_id, token)
    return request_id


@router.get("/health", tags=["sistema"])
def health(p: DonationPlatform = Depends(get_platform)) -> dict:
    return {"status": "ok", "agente_con_ia": p.ai_enabled, "proveedor_ia": p.ai_provider}


# ---------- 1. Registro y perfil del donante ----------
@router.post("/donors", response_model=DonorOut, status_code=201, tags=["donantes"])
def register_donor(body: DonorIn, p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.register_donor(RegisterDonorCommand(**body.model_dump())))


@router.post("/auth/login", response_model=SessionOut, tags=["donantes"])
def login(body: LoginIn, p: DonationPlatform = Depends(get_platform)):
    session = p.login(body.email, body.password)
    return SessionOut(access_token=session.token, donor=DonorOut.of(session.donor))


@router.get("/me", response_model=DonorOut, tags=["donantes"])
def my_profile(donor_id: str = Depends(current_donor_id), p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.get_donor(donor_id))


@router.patch("/me", response_model=DonorOut, tags=["donantes"])
def update_my_profile(body: ProfileUpdateIn, donor_id: str = Depends(current_donor_id),
                      p: DonationPlatform = Depends(get_platform)):
    return DonorOut.of(p.update_profile(donor_id, UpdateProfileCommand(**body.model_dump())))


@router.get("/me/donations", response_model=DonationHistoryOut, tags=["donantes"])
def my_donations(donor_id: str = Depends(current_donor_id), p: DonationPlatform = Depends(get_platform)):
    return DonationHistoryOut.of(p.donation_history(donor_id))


@router.get("/me/alerts", response_model=list[AlertOut], tags=["donantes"])
def my_alerts(donor_id: str = Depends(current_donor_id), p: DonationPlatform = Depends(get_platform)):
    return [AlertOut.of(a) for a in p.alerts_for_donor(donor_id)]


# ---------- 2. Cuestionario de tamizaje ----------
@router.post("/me/screening", response_model=EligibilityOut, tags=["tamizaje"])
def submit_screening(body: ScreeningIn, donor_id: str = Depends(current_donor_id),
                     p: DonationPlatform = Depends(get_platform)):
    return EligibilityOut.of(p.submit_screening(donor_id, ScreeningAnswers(**body.model_dump())))


# ---------- 3. Solicitudes de sangre ----------
@router.get("/hospitals", response_model=list[HospitalOut], tags=["solicitudes"])
def list_hospitals(p: DonationPlatform = Depends(get_platform)):
    return [HospitalOut(id=hospital_id, name=name) for hospital_id, name in p.list_hospitals()]


@router.post("/requests", response_model=CreatedRequestOut, status_code=201, tags=["solicitudes"])
def create_request(body: RequestIn, p: DonationPlatform = Depends(get_platform)):
    fields = body.model_dump(exclude={"hours_valid"})
    request = p.create_request_valid_for(body.hours_valid, **fields)
    return CreatedRequestOut(**RequestOut.of(request).model_dump(), manage_token=p.request_token(request.id))


@router.get("/requests/{request_id}", response_model=RequestOut, tags=["solicitudes"])
def get_request(request_id: str, p: DonationPlatform = Depends(get_platform)):
    return RequestOut.of(p.get_request(request_id))


@router.get("/requests/{request_id}/alerts", response_model=list[AlertOut], tags=["solicitudes"])
def request_alerts(request_id: str = Depends(request_owner), p: DonationPlatform = Depends(get_platform)):
    return [AlertOut.of(a) for a in p.alerts_for_request(request_id)]


@router.post("/requests/{request_id}/confirm", response_model=RequestOut, tags=["solicitudes"])
def confirm_donation(request_id: str, donor_id: str = Depends(current_donor_id),
                     p: DonationPlatform = Depends(get_platform)):
    return RequestOut.of(p.confirm_donation(request_id, donor_id))


# ---------- 4. Agente de priorización y matching ----------
@router.get("/requests/{request_id}/candidates", response_model=list[CandidateOut], tags=["agente"])
def preview_candidates(request_id: str = Depends(request_owner), p: DonationPlatform = Depends(get_platform)):
    return [CandidateOut.of(i, c) for i, c in enumerate(p.preview_candidates(request_id), start=1)]


@router.post("/requests/{request_id}/dispatch", response_model=list[AlertOut], tags=["agente"])
def dispatch_wave(request_id: str = Depends(request_owner), p: DonationPlatform = Depends(get_platform)):
    return [AlertOut.of(a) for a in p.dispatch_wave(request_id)]


@router.post("/requests/escalate", response_model=dict[str, list[AlertOut]], tags=["agente"])
def escalate(p: DonationPlatform = Depends(get_platform)):
    return {rid: [AlertOut.of(a) for a in alerts] for rid, alerts in p.escalate().items()}
