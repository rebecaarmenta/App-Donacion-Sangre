"""Punto de entrada de la API.

    uvicorn donacion.main:app --reload --app-dir src
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .container import build_platform
from .domain.errors import AuthenticationError, ConflictError, DomainError, NotFoundError
from .services.platform import DonationPlatform

WEB_DIR = Path(__file__).parent / "web" / "static"

_STATUS = {NotFoundError: 404, ConflictError: 409, AuthenticationError: 401}


def create_app(platform: DonationPlatform | None = None) -> FastAPI:
    app = FastAPI(
        title="Plataforma Agéntica de Donación de Sangre - MVP",
        description="Registro de donantes, tamizaje (NOM-253), solicitudes y agente de priorización.",
        version="0.1.0",
    )
    app.state.platform = platform or build_platform()

    @app.exception_handler(DomainError)
    def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        status = next((code for cls, code in _STATUS.items() if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    app.include_router(router)
    app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web")

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse("/app/")

    return app


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = create_app()

if os.getenv("DONACION_SEED_DEMO", "1") == "1":
    from .demo import seed_demo
    seed_demo(app.state.platform)
