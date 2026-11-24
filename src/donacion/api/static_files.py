"""Archivos de la interfaz web con "Cache-Control: no-cache".

no-cache no impide guardar los archivos: obliga al navegador a preguntar si cambiaron antes de
usarlos (responde 304 si siguen iguales). Así, tras actualizar la app, nunca se mezclan módulos
JavaScript viejos y nuevos.
"""
from __future__ import annotations

from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response
