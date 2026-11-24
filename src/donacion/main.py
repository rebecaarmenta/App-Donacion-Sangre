"""Punto de entrada de la API.

    uvicorn donacion.main:app --reload --app-dir src
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .adapters.escalation_scheduler import EscalationScheduler
from .api.routes import router
from .api.static_files import NoCacheStaticFiles
from .config import Settings
from .container import build_platform
from .domain.errors import AuthenticationError, ConflictError, DomainError, ForbiddenError, NotFoundError
from .services.platform import DonationPlatform

WEB_DIR = Path(__file__).parent / "web" / "static"

_STATUS = {NotFoundError: 404, ConflictError: 409, AuthenticationError: 401, ForbiddenError: 403}


def create_app(platform: DonationPlatform | None = None, auto_escalate: bool = False,
               escalation_check_seconds: float = 30.0) -> FastAPI:
    """auto_escalate=True revisa cada escalation_check_seconds si toca enviar otra oleada.
    Solo corre mientras el servidor está levantado (lifespan)."""
    platform = platform or build_platform()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if not auto_escalate:
            yield
            return
        scheduler = EscalationScheduler(platform.escalate, escalation_check_seconds)
        scheduler.start()
        try:
            yield
        finally:
            scheduler.stop()

    app = FastAPI(
        lifespan=lifespan,
        title="Plataforma Agéntica de Donación de Sangre",
        description="Registro de donantes, tamizaje (NOM-253), solicitudes y agente de priorización.",
        version="1.0.0",
    )
    app.state.platform = platform

    @app.exception_handler(DomainError)
    def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        status = next((code for cls, code in _STATUS.items() if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    app.include_router(router)
    app.mount("/app", NoCacheStaticFiles(directory=WEB_DIR, html=True), name="web")

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse("/app/")

    return app


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
settings = Settings.from_env()
app = create_app(build_platform(settings=settings), auto_escalate=settings.auto_escalate,
                 escalation_check_seconds=settings.escalation_check_seconds)

if settings.seed_demo:
    from .demo import seed_demo
    seed_demo(app.state.platform)
