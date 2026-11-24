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


DONANTE_IDS = ["form-registro", "form-acceso", "seccion-perfil", "perfil-nombre", "perfil-tipo",
               "perfil-estado", "form-perfil", "form-tamizaje", "lista-donaciones", "historial-resumen", "lista-alertas", "btn-salir", "mensaje"]


def test_pagina_donante_tiene_los_elementos_que_usa_su_script():
    html = client().get("/app/donante.html").text
    for element_id in DONANTE_IDS:
        assert f'id="{element_id}"' in html, element_id
    assert 'src="js/donante.js"' in html and 'type="module"' in html


SOLICITUD_IDS = ["form-solicitud", "seccion-estado", "estado-resumen", "tabla-candidatos", "btn-candidatos",
                 "btn-oleada", "lista-oleadas", "mensaje"]


def test_la_pagina_de_solicitud_no_muestra_el_proveedor_de_ia():
    html = client().get("/app/solicitud.html").text
    assert "indicador-ia" not in html and "Ollama" not in html


def test_pagina_solicitud_tiene_los_elementos_que_usa_su_script():
    html = client().get("/app/solicitud.html").text
    for element_id in SOLICITUD_IDS:
        assert f'id="{element_id}"' in html, element_id
    assert 'src="js/solicitud.js"' in html and 'type="module"' in html


def test_el_navegador_siempre_revisa_si_cambiaron_los_archivos():
    # Sin esto, el navegador mezcla archivos viejos y nuevos tras una actualización
    # (p. ej. un donante.js nuevo que pide una función que el format.js guardado no tiene).
    c = client()
    for path in ("/app/", "/app/donante.html", "/app/js/format.js", "/app/css/app.css"):
        assert c.get(path).headers["cache-control"] == "no-cache", path


def test_la_pagina_del_donante_no_muestra_cuentas_de_prueba():
    assert "Cuentas de prueba" not in client().get("/app/donante.html").text


def test_cada_pagina_programa_su_actualizacion_una_sola_vez():
    # Un setInterval dentro de una función se acumula en cada clic y satura al servidor.
    from pathlib import Path
    js = Path(__file__).resolve().parents[1] / "src" / "donacion" / "web" / "static" / "js"
    for name in ("donante.js", "solicitud.js"):
        lines = (js / name).read_text().splitlines()
        timers = [line for line in lines if "setInterval(" in line]
        assert len(timers) == 1, name
        assert timers[0].startswith("setInterval("), name     # al nivel del módulo, sin sangría
        assert lines[-1].startswith("setInterval("), name     # y es lo último que se ejecuta
