"""La app sirve la interfaz web en /app con la paleta acordada."""
import re

from fastapi.testclient import TestClient

from donacion.container import build_platform
from donacion.main import create_app


def client():
    return TestClient(create_app(build_platform(use_llm=False)), follow_redirects=False)


def test_raiz_redirige_a_la_app():
    r = client().get("/")
    assert r.status_code in (307, 308)
    assert r.headers["location"] == "/app/"


def test_portada_enlaza_las_dos_paginas():
    html = client().get("/app/").text
    assert 'href="donante.html"' in html and 'href="solicitud.html"' in html
    assert "/app/css/app.css" in html


def test_la_api_sigue_funcionando():
    assert client().get("/health").json()["status"] == "ok"


PALETA = {"--rojo": "#b5545d", "--rojo-pastel": "#e8a3a9", "--rojo-claro": "#f7e4e5", "--fondo": "#ffffff",
          "--fondo-suave": "#faf6f6", "--texto": "#3d3535", "--texto-suave": "#7a6e6e", "--borde": "#eadddd"}


def test_la_hoja_de_estilos_usa_solo_la_paleta():
    css = client().get("/app/css/app.css").text.lower()
    for name, value in PALETA.items():
        assert f"{name}: {value}" in css, name
    colores = set(re.findall(r"#[0-9a-f]{6}\b", css))
    assert colores <= set(PALETA.values())
