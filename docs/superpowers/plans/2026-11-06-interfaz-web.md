# Refactorización OO del backend + Interfaz web – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Refactorizar el backend del MVP para demostrar con evidencia SOLID, refactorización, Factory Method, Facade, Adapter y Strategy; (2) agregar una interfaz web en tonos blanco y rojo pastel que se corre en `http://localhost:8000`.

**Architecture:** El backend conserva su arquitectura por capas (dominio → servicios → API, con puertos y adaptadores). Las Tasks 1–3 son refactorizaciones con las 39 pruebas como red de seguridad: primero quitan olores de código (DIP roto, duplicación, clases con dos responsabilidades, números mágicos) y luego introducen **Factory Method** para construir el agente y una **Facade** (`DonationPlatform`) como única entrada de la API. La Task 4 documenta cada concepto con su archivo. La interfaz (Tasks 5–9) son páginas estáticas servidas por FastAPI en `/app`, con la lógica probable en módulos JS puros; el frontend no necesita ser OO (acordado con el profesor).

**Tech Stack:** Python 3.11+, FastAPI 0.162 (`StaticFiles`), uvicorn, pytest; JavaScript ES modules sin framework; `node --test` (Node 22).

**Spec:** `docs/vision_y_alcances_v2.pdf` (secciones 5–7), tabla de endpoints del `README.md`, y los temas del curso (SOLID, refactorización, Factory Method, Adapter, Facade).

## Global Constraints

- Cada refactorización (Tasks 1–3) se hace con las pruebas en verde antes y después: `.venv/bin/python -m pytest -q`. Una refactorización no cambia el comportamiento de la API.
- Un commit por refactorización, con mensaje `refactor: <técnica>: <qué>`; esos commits son la evidencia de la refactorización.
- Factory Method con la misma forma que la vista en clase: clase creadora abstracta con métodos fábrica abstractos + fábricas concretas.
- La API (`api/routes.py`) depende solo de la fachada `DonationPlatform`, nunca de servicios ni adaptadores concretos.
- Se corre en localhost: `python run.py` levanta `http://localhost:8000` (host `127.0.0.1`, puerto `8000`); `/` redirige a `/app/`.
- Paleta del frontend (variables CSS exactas, sin otros colores): `--rojo: #b5545d` (botones y títulos; contraste 4.8:1 con blanco), `--rojo-pastel: #e8a3a9` (acentos y bordes destacados), `--rojo-claro: #f7e4e5` (fondos suaves), `--fondo: #ffffff`, `--fondo-suave: #faf6f6`, `--texto: #3d3535`, `--texto-suave: #7a6e6e`, `--borde: #eadddd`.
- Texto visible en español; urgencias con acento al mostrarlas (`critica` → "crítica").
- Sin dependencias nuevas de Python ni npm; sin CDN ni recursos externos.
- Ningún dato del usuario se inserta con `innerHTML` sin `escapeHtml`; preferir `textContent`.
- Sesión del MVP = `donorId` en `localStorage` (sin tokens; se documenta).
- Fuera de alcance: mapa de campañas y estadísticas regionales.

## Review Focus

1. **Errores 422 de FastAPI:** `detail` es una lista de objetos; la UI debe mostrar "birth_date: …" legible, nunca `[object Object]`. → prueba en Task 6 (`errorMessage`).
2. **Servidor reiniciado:** los datos son en memoria; el `donorId` guardado da 404 y la UI debe cerrar la sesión. → prueba en Task 6 (`sessionAfterError`).
3. **Fechas vacías del formulario:** `""` debe omitirse del payload (si no, 422). → prueba en Task 6 (payloads).
4. **Nombres con HTML o acentos:** se muestran literales y con acentos. → prueba en Task 6 (`escapeHtml`).
5. **Refactorización que cambia el comportamiento sin querer:** el orden de candidatos con los pesos por defecto debe ser idéntico al de antes de `ScoringWeights`. → prueba en Task 2 (`test_pesos_por_defecto_conservan_el_orden`).

---

## File Structure

```
# Backend (refactorización)
src/donacion/ports/alert_log.py           (crear)  puerto AlertLog
src/donacion/ports/ids.py                 (crear)  puerto IdGenerator
src/donacion/adapters/memory_alert_log.py (crear)
src/donacion/adapters/uuid_ids.py         (crear)
src/donacion/adapters/console_notifier.py (modificar) ya no guarda bandeja
src/donacion/domain/response_history.py   (crear)  value object extraído de Donor
src/donacion/domain/donor.py              (modificar)
src/donacion/agent/weights.py             (crear)  ScoringWeights
src/donacion/agent/prompts.py             (crear)  RerankPromptBuilder, ExplanationPromptBuilder
src/donacion/agent/scoring.py, explanation.py (modificar)
src/donacion/agent/factory.py             (crear)  Factory Method del agente
src/donacion/services/request_finder.py   (crear)  búsqueda compartida de solicitudes
src/donacion/services/platform.py         (crear)  Facade DonationPlatform
src/donacion/services/*.py                (modificar)
src/donacion/container.py, api/routes.py, main.py (modificar)
run.py                                    (crear)  arranque en localhost
docs/patrones_y_solid.md, docs/refactorizacion.md (crear); docs/diagrama_clases.md (modificar)
tests/test_refactor.py, tests/test_factory_facade.py (crear)

# Frontend
src/donacion/web/static/{index,donante,solicitud}.html
src/donacion/web/static/css/app.css
src/donacion/web/static/js/{format,payloads,catalogs,session,api,donante,solicitud}.js
tests/test_web.py, tests/web/*.test.mjs
```

---

### Task 1: Refactorización — Dependency Inversion en las alertas e IDs inyectables

**Olores que corrige:** la ruta `/donors/{id}/alerts` llama a `ConsoleNotifier.sent_to()` (clase concreta, viola DIP: cambiar a push la rompería); `ConsoleNotifier` envía **y** guarda (dos responsabilidades); `lambda: uuid.uuid4().hex[:8]` duplicado en dos servicios.

**Files:**
- Create: `src/donacion/ports/alert_log.py`, `src/donacion/ports/ids.py`, `src/donacion/adapters/memory_alert_log.py`, `src/donacion/adapters/uuid_ids.py`, `tests/test_refactor.py`
- Modify: `adapters/console_notifier.py`, `services/matching_service.py`, `services/donor_service.py`, `services/request_service.py`, `container.py`, `api/routes.py`

**Interfaces:**
- Produces:
  - `class AlertLog(ABC)`: `record(alert: Alert) -> None`, `for_donor(donor_id: str) -> list[Alert]`, `for_request(request_id: str) -> list[Alert]`; impl `InMemoryAlertLog`.
  - `class IdGenerator(ABC)`: `new_id() -> str`; impl `UuidIdGenerator(length: int = 8)`.
  - `MatchingService.__init__(agent, donors, requests, notifier: Notifier, alert_log: AlertLog, clock)`; nuevo `MatchingService.alerts_for_donor(donor_id: str) -> list[Alert]`.
  - `DonorService.__init__(repository, hasher, ids: IdGenerator)`; `RequestService.__init__(requests, donors, clock, donation_interval_days, ids: IdGenerator)`.
  - `ConsoleNotifier` solo implementa `send` (sin `sent_to`/`sent_for`).
  - `Container` cambia el campo `notifier` por `alert_log: AlertLog`.

- [ ] **Step 1: Git y línea base** — `git init`, `git add . && git commit -m "chore: MVP inicial"`; correr `.venv/bin/python -m pytest -q` → `39 passed`.
- [ ] **Step 2: Write the failing tests** en `tests/test_refactor.py`

```python
class SpyNotifier(Notifier):
    def __init__(self): self.sent = []
    def send(self, alert): self.sent.append(alert)

class SequentialIds(IdGenerator):
    def __init__(self, prefix): self.prefix, self.n = prefix, 0
    def new_id(self): self.n += 1; return f"{self.prefix}{self.n}"

def test_las_alertas_se_registran_en_el_log_y_no_en_el_notificador(clock):
    # MatchingService con SpyNotifier + InMemoryAlertLog, 1 donante apto A+ y una solicitud A+
    ...
    alerts = matching.dispatch(request.id)
    assert spy.sent == alerts
    assert matching.alerts_for_donor(donor.id) == alerts
    assert alert_log.for_request(request.id) == alerts

def test_ids_inyectados():
    service = DonorService(InMemoryDonorRepository(), Pbkdf2Hasher(), SequentialIds("d"))
    assert service.register(<RegisterDonorCommand válido>).id == "d1"

def test_console_notifier_solo_envia():
    assert not hasattr(ConsoleNotifier(), "sent_to")
```

- [ ] **Step 3: Run** — `.venv/bin/python -m pytest tests/test_refactor.py -v` → FAIL (imports inexistentes).
- [ ] **Step 4: Implement** los puertos, adaptadores y cambios de constructor; la ruta `/donors/{id}/alerts` usa `matching.alerts_for_donor`. Ajustar en `container.py` y en `tests/test_api.py` solo lo necesario para los nuevos constructores.
- [ ] **Step 5: Run** — `.venv/bin/python -m pytest -q` → todas pasan.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "refactor: inversión de dependencias: AlertLog e IdGenerator"`

---

### Task 2: Refactorización — Extract Class, Parameter Object y eliminación de duplicados

**Olores que corrige:** `Donor` maneja perfil **y** estadísticas de respuesta (SRP); pesos `45/25/30/-20/0.6/30 km` escritos dentro de `RuleBasedScoring` (números mágicos); `LLMAssistedScoring` y `LLMExplanation` ordenan/explican **y** arman prompts (SRP); `RequestService.get` y `MatchingService._get_open` duplican "buscar + vencer" (DRY).

**Files:**
- Create: `src/donacion/domain/response_history.py`, `src/donacion/agent/weights.py`, `src/donacion/agent/prompts.py`, `src/donacion/services/request_finder.py`
- Modify: `domain/donor.py`, `agent/scoring.py`, `agent/explanation.py`, `services/request_service.py`, `services/matching_service.py`, `container.py`
- Test: `tests/test_refactor.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class ResponseHistory`: `received: int = 0`, `accepted: int = 0`; `rate -> float` (0.5 si `received == 0`); `with_alert() -> ResponseHistory`; `with_acceptance() -> ResponseHistory`. `Donor` guarda `_history: ResponseHistory`, expone `response_history` y conserva `response_rate`, `register_alert()`, `record_donation(...)` con la misma conducta.
  - `@dataclass(frozen=True) class ScoringWeights`: `proximity=45.0`, `blood_match=25.0`, `compatible_factor=0.6`, `response=30.0`, `universal_reserve_penalty=20.0`, `reference_km=30.0`. `RuleBasedScoring(weights: ScoringWeights = ScoringWeights())` (reemplaza el parámetro `reference_km`).
  - `class RerankPromptBuilder`: atributos `system: str`, `schema: dict`; `build(candidates: list[RankedCandidate], request: BloodRequest) -> str`. `class ExplanationPromptBuilder`: igual, `build(wave, request) -> str`. Constantes `_RERANK_*` / `_EXPLAIN_*` se mueven aquí. `LLMAssistedScoring(llm, base, top_n=15, prompts: RerankPromptBuilder = RerankPromptBuilder())`; `LLMExplanation(llm, fallback, prompts: ExplanationPromptBuilder = ExplanationPromptBuilder())`.
  - `class RequestFinder(requests: RequestRepository, clock: Clock)`: `get(request_id) -> BloodRequest` (404 + `expire_if_needed`), `get_open(request_id) -> BloodRequest` (además 409 si no está abierta). `RequestService` y `MatchingService` reciben un `RequestFinder` y borran su copia.

- [ ] **Step 1: Write the failing tests** (agregar a `tests/test_refactor.py`)

```python
def test_historial_de_respuesta_es_inmutable_y_calcula_la_tasa():
    h = ResponseHistory()
    assert h.rate == 0.5
    h2 = h.with_alert().with_alert().with_acceptance()
    assert (h.received, h2.received, h2.accepted, h2.rate) == (0, 2, 1, 0.5)

def test_pesos_por_defecto_conservan_el_orden():
    # mismos donantes que test_agent: orden con RuleBasedScoring() == orden con RuleBasedScoring(ScoringWeights())
    ...

def test_pesos_configurables_cambian_la_prioridad():
    cerca = make_donor("cerca", lat=20.687, lon=-103.35)            # tasa 0.5 (sin historial)
    lejos = make_donor("lejos", lat=20.55, lon=-103.45)              # ~18 km
    for _ in range(2):
        lejos.register_alert()
        lejos.record_donation(date(2026, 1, 1), date(2026, 3, 1))     # tasa 1.0
    assert RuleBasedScoring().rank([cerca, lejos], request())[0].donor.id == "cerca"
    only_response = ScoringWeights(proximity=0, blood_match=0, response=100)
    assert RuleBasedScoring(only_response).rank([cerca, lejos], request())[0].donor.id == "lejos"

def test_prompt_builder_no_envia_datos_personales():
    text = RerankPromptBuilder().build([<candidato "Ana López", ana@demo.mx>], request())
    assert "Ana" not in text and "@" not in text and "donor_id" in text

def test_request_finder_vence_y_rechaza_cerradas(clock):
    # solicitud con deadline +1h; clock.advance(61) → get() la devuelve "vencida"; get_open() lanza ConflictError
    ...
```

- [ ] **Step 2: Run** — FAIL (clases inexistentes).
- [ ] **Step 3: Implement** las cuatro extracciones (una por una, corriendo `pytest -q` y haciendo commit después de cada una):
  - `refactor: extract class: ResponseHistory`
  - `refactor: introduce parameter object: ScoringWeights`
  - `refactor: extract class: constructores de prompts`
  - `refactor: eliminar duplicación: RequestFinder`
- [ ] **Step 4: Run** — `.venv/bin/python -m pytest -q` → todas pasan, incluidas las 39 originales.

---

### Task 3: Patrones — Factory Method del agente y Facade de la plataforma

**Files:**
- Create: `src/donacion/agent/factory.py`, `src/donacion/services/platform.py`, `tests/test_factory_facade.py`, `run.py`
- Modify: `container.py`, `api/routes.py`, `main.py`, `tests/test_api.py` (solo construcción)

**Interfaces:**
- Produces:
  - Factory Method (`agent/factory.py`):
    ```python
    class MatchingAgentFactory(ABC):            # clase creadora
        @abstractmethod
        def create_scoring(self) -> ScoringStrategy: ...        # método fábrica
        @abstractmethod
        def create_explainer(self) -> ExplanationBuilder: ...   # método fábrica
        def create_filters(self) -> list[CandidateFilter]       # por defecto: Compatibility, Eligibility, MaxDistance(50)
        def create_planner(self) -> WavePlanner                  # por defecto: WavePlanner(10, 15)
        def build(self) -> MatchingAgent                         # usa los métodos fábrica
    class RuleBasedAgentFactory(MatchingAgentFactory)            # fábrica concreta
    class AIAgentFactory(MatchingAgentFactory):                  # fábrica concreta
        def __init__(self, llm: LLMClient): ...
    ```
    `AIAgentFactory.create_scoring()` → `LLMAssistedScoring(llm, RuleBasedScoring())`; `create_explainer()` → `LLMExplanation(llm, TemplateExplanation())`.
  - Facade (`services/platform.py`): `class DonationPlatform(donors: DonorService, screening: ScreeningService, requests: RequestService, matching: MatchingService, clock: Clock, ai_enabled: bool)` con: `register_donor(cmd)`, `login(email, password)`, `get_donor(id)`, `list_donors()`, `submit_screening(donor_id, answers)`, `alerts_for_donor(donor_id)`, `create_request(cmd)`, `create_request_valid_for(hours: int, **fields)`, `get_request(id)`, `confirm_donation(request_id, donor_id)`, `preview_candidates(request_id)`, `dispatch_wave(request_id)`, `escalate()`, propiedad `ai_enabled`.
  - `build_platform(use_llm: bool | None = None, clock: Clock | None = None, llm_client: LLMClient | None = None) -> DonationPlatform` en `container.py` (reemplaza `build_container`/`Container`); elige `AIAgentFactory` o `RuleBasedAgentFactory`.
  - `create_app(platform: DonationPlatform | None = None)`; `routes.get_platform(request) -> DonationPlatform`; `seed_demo(platform)`.
  - `run.py`: agrega `src` al `sys.path`, imprime `Abre http://localhost:8000 en tu navegador` y llama `uvicorn.run("donacion.main:app", host="127.0.0.1", port=8000)`.

- [ ] **Step 1: Write the failing tests** en `tests/test_factory_facade.py`

```python
def test_fabrica_por_reglas_crea_agente_sin_ia():
    agent = RuleBasedAgentFactory().build()
    assert isinstance(agent, MatchingAgent)
    assert isinstance(RuleBasedAgentFactory().create_scoring(), RuleBasedScoring)

def test_fabrica_con_ia_crea_estrategias_con_respaldo():
    factory = AIAgentFactory(FakeLLM(fail=True))
    assert isinstance(factory.create_scoring(), LLMAssistedScoring)
    assert isinstance(factory.create_explainer(), LLMExplanation)

def test_las_fabricas_son_intercambiables(clock):         # Liskov
    for factory in (RuleBasedAgentFactory(), AIAgentFactory(FakeLLM(fail=True))):
        alerts = factory.build().plan_wave(request(), [make_donor("d1")], NOW)
        assert [a.donor_id for a in alerts] == ["d1"]

def test_build_platform_elige_la_fabrica():
    assert build_platform(use_llm=False).ai_enabled is False
    assert build_platform(use_llm=True, llm_client=FakeLLM(fail=True)).ai_enabled is True

def test_la_api_solo_depende_de_la_fachada():
    source = Path("src/donacion/api/routes.py").read_text()
    assert "DonationPlatform" in source
    for concrete in ("DonorService", "MatchingService", "RequestService", "ScreeningService", "adapters"):
        assert concrete not in source
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** fábrica, fachada, `build_platform`, rutas sobre la fachada, `main.py`, `demo.py`, `scripts/demo_cli.py`, `run.py`. Mover `FakeLLM` de `tests/test_agent.py` a `tests/conftest.py` para reutilizarlo.
- [ ] **Step 4: Run** — `.venv/bin/python -m pytest -q` → todas pasan.
- [ ] **Step 5: Verificar localhost** — `.venv/bin/python run.py` → imprime la URL; `curl -s http://localhost:8000/health` → `{"status":"ok",...}`; Ctrl+C.
- [ ] **Step 6: Commits** — `git commit -m "feat: patrón Factory Method para construir el agente"` y `git commit -m "feat: patrón Facade DonationPlatform para la API"` (uno por patrón).

---

### Task 4: Documentación de diseño para el profesor

**Files:**
- Create: `docs/patrones_y_solid.md`, `docs/refactorizacion.md`
- Modify: `docs/diagrama_clases.md`, `README.md`

- [ ] **Step 1: `docs/patrones_y_solid.md`** — una sección por concepto, cada una con: qué es (1–2 oraciones), **dónde está** (ruta del archivo y clase), y por qué se usó aquí. Conceptos: S, O, L, I, D; encapsulamiento; herencia y polimorfismo; Factory Method (`agent/factory.py`, comparar con la estructura creadora/productos vista en clase); Facade (`services/platform.py`); Adapter (`adapters/claude_llm_client.py`, `adapters/memory_*`); Strategy (`agent/scoring.py`, `agent/explanation.py`); Template Method (`screening/rules.py: _WaitingPeriodRule` y `MatchingAgentFactory.build`); Repository; inyección de dependencias / composition root (`container.py`).
- [ ] **Step 2: `docs/refactorizacion.md`** — por cada refactorización de las Tasks 1–2: olor de código, técnica (nombre de Fowler), antes (fragmento de 3–6 líneas), después, y el hash del commit (`git log --oneline`). Cerrar con "las 39 pruebas originales pasaron antes y después de cada cambio".
- [ ] **Step 3: Diagrama** — agregar al Mermaid: `AlertLog`, `IdGenerator`, `ResponseHistory`, `ScoringWeights`, prompt builders, `RequestFinder`, `MatchingAgentFactory` y sus dos fábricas, `DonationPlatform`; quitar `ConsoleNotifier.sent_to`.
- [ ] **Step 4: README** — enlazar los dos documentos nuevos; cambiar "Cómo correrlo" a `python run.py` → `http://localhost:8000`; actualizar la sección SOLID con Factory Method y Facade.
- [ ] **Step 5: Commit** — `git commit -m "docs: patrones, SOLID y bitácora de refactorización"`

---

### Task 5: Servir la interfaz con la paleta blanco / rojo pastel

**Files:**
- Modify: `src/donacion/main.py` (dentro de `create_app`)
- Create: `src/donacion/web/__init__.py`, `src/donacion/web/static/index.html`, `src/donacion/web/static/css/app.css`
- Test: `tests/test_web.py`

**Interfaces:**
- Produces: `/app/` sirve `web/static`; `GET /` (fuera del esquema) redirige a `/app/`; todas las páginas cargan `/app/css/app.css`; clases CSS: `.card`, `.btn`, `.btn-secundario`, `.error`, `.ok`, `.insignia`, `.insignia-apto`, `.insignia-diferido`, `.insignia-no_apto`, `.insignia-pendiente`, `.oculto`.

- [ ] **Step 1: Write the failing test** en `tests/test_web.py`

```python
def client():
    return TestClient(create_app(build_platform(use_llm=False)), follow_redirects=False)

def test_raiz_redirige_a_la_app():
    r = client().get("/")
    assert r.status_code in (307, 308) and r.headers["location"] == "/app/"

def test_portada_enlaza_las_dos_paginas():
    html = client().get("/app/").text
    assert 'href="donante.html"' in html and 'href="solicitud.html"' in html and "/app/css/app.css" in html

PALETA = {"--rojo": "#b5545d", "--rojo-pastel": "#e8a3a9", "--rojo-claro": "#f7e4e5", "--fondo": "#ffffff",
          "--fondo-suave": "#faf6f6", "--texto": "#3d3535", "--texto-suave": "#7a6e6e", "--borde": "#eadddd"}

def test_la_hoja_de_estilos_usa_solo_la_paleta():
    css = client().get("/app/css/app.css").text.lower()
    for name, value in PALETA.items():
        assert f"{name}: {value}" in css
    colores = set(re.findall(r"#[0-9a-f]{6}\b", css))
    assert colores <= set(PALETA.values())
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** — `app.mount("/app", StaticFiles(directory=Path(__file__).parent / "web" / "static", html=True))` + `RedirectResponse("/app/")`. `index.html`: encabezado blanco con una línea inferior `--rojo-pastel`, título "Donación de sangre" en `--rojo`, dos tarjetas ("Soy donante", "Necesito sangre"). `app.css`: variables de la paleta en `:root`; fuente del sistema; fondo `--fondo-suave`; tarjetas blancas con borde `--borde` y radio 12 px; botones `--rojo` con texto blanco, y `.btn-secundario` blanco con borde `--rojo-pastel`. Insignias solo con la paleta: apto (fondo `--rojo-claro`, texto `--rojo`), diferido (fondo `--fondo-suave`, borde `--rojo-pastel`), no apto (fondo `--borde`, texto `--texto`), pendiente (blanco, borde `--borde`, texto `--texto-suave`). El estado siempre va en texto, no solo en color.
- [ ] **Step 4: Run** — `.venv/bin/python -m pytest -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(web): servir interfaz en /app con paleta blanco y rojo pastel"`

---

### Task 6: Módulos puros de la interfaz (formato, payloads, catálogos, sesión)

**Files:**
- Create: `src/donacion/web/static/js/format.js`, `payloads.js`, `catalogs.js`, `session.js`
- Test: `tests/web/format.test.mjs`, `tests/web/payloads.test.mjs`, `tests/web/session.test.mjs`

**Interfaces (`export` de ES modules):**
- `format.js`: `escapeHtml(text)`; `errorMessage(detail: string | Array<{loc, msg}> | undefined, status: number)`; `urgencyLabel("critica"|"alta"|"normal")`; `statusLabel(value)` (`apto→"Apto"`, `diferido→"Diferido"`, `no_apto→"No apto"`, `pendiente→"Pendiente"`, `abierta→"Abierta"`, `cubierta→"Cubierta"`, `vencida→"Vencida"`, otro → igual); `eligibilityText({status, reasons, eligible_from})`; `describeDispatch(alerts)`.
- `payloads.js`: `buildDonorPayload(form, zone: {lat, lon})`; `buildScreeningPayload(form)`; `buildRequestPayload(form, hospital: {name, lat, lon})`.
- `catalogs.js`: `ZONES` — Centro GDL (20.6767, -103.3475), Chapultepec (20.6720, -103.3700), Zapopan Centro (20.7214, -103.3918), Tlaquepaque (20.6400, -103.3100), Tonalá (20.6240, -103.2340), Tlajomulco (20.4736, -103.4440); `HOSPITALS` — Hospital Civil Fray Antonio Alcalde (20.6866, -103.3496), Hospital Civil Juan I. Menchaca (20.6981, -103.3324), Centro Médico Nacional de Occidente (20.6835, -103.3266), Centro Estatal de la Transfusión Sanguínea (20.6731, -103.3600). Cada uno `{id, name, lat, lon}`.
- `session.js`: `createSession(storage)` → `{get(), set(donorId), clear()}` con clave `"donacion.donorId"`; `sessionAfterError(status)` → `"clear"` si 404, si no `"keep"`.

- [ ] **Step 1: Write the failing tests**

```js
// tests/web/format.test.mjs
test("escapa HTML y conserva acentos", () =>
  assert.equal(escapeHtml(`<b>Núñez</b> & "x"`), "&lt;b&gt;Núñez&lt;/b&gt; &amp; &quot;x&quot;"));
test("error de dominio en texto", () =>
  assert.equal(errorMessage("Ya existe un donante con ese correo", 409), "Ya existe un donante con ese correo"));
test("error 422 en lista se vuelve legible", () => assert.equal(
  errorMessage([{ loc: ["body", "birth_date"], msg: "Input should be a valid date" },
                { loc: ["body", "weight_kg"], msg: "Input should be greater than 0" }], 422),
  "birth_date: Input should be a valid date. weight_kg: Input should be greater than 0"));
test("sin detalle usa el código", () => assert.equal(errorMessage(undefined, 500), "Error del servidor (500)"));
test("etiquetas", () => { assert.equal(urgencyLabel("critica"), "crítica");
  assert.equal(statusLabel("no_apto"), "No apto"); assert.equal(statusLabel("cubierta"), "Cubierta"); });
test("elegibilidad diferida con fecha", () => assert.equal(
  eligibilityText({ status: "diferido", reasons: ["Tatuaje"], eligible_from: "2027-08-06" }),
  "Diferido: Tatuaje. Podrás donar desde el 2027-08-06."));
test("oleadas", () => { assert.equal(describeDispatch([]), "Ya no quedan donantes compatibles por avisar.");
  assert.equal(describeDispatch([{ wave: 2 }, { wave: 2 }]), "Oleada 2 enviada a 2 donantes."); });
```

```js
// tests/web/payloads.test.mjs
test("donante: números y sin última donación vacía", () => assert.deepEqual(
  buildDonorPayload({ name: "Ana", email: "a@a.mx", password: "segura123", birth_date: "2000-01-02",
    weight_kg: "61.5", blood_type: "O+", last_donation: "" }, { lat: 20.67, lon: -103.34 }),
  { name: "Ana", email: "a@a.mx", password: "segura123", birth_date: "2000-01-02", weight_kg: 61.5,
    blood_type: "O+", lat: 20.67, lon: -103.34 }));
test("tamizaje: omite fechas vacías", () => assert.deepEqual(
  buildScreeningPayload({ tattoo_or_piercing_date: "", surgery_date: "2026-10-01", medication_end_date: "",
    permanent_exclusion: false }), { surgery_date: "2026-10-01", permanent_exclusion: false }));
test("solicitud con hospital del catálogo", () => assert.deepEqual(
  buildRequestPayload({ requester_name: "Familia", blood_type: "A+", units_needed: "2", urgency: "critica",
    hours_valid: "12" }, { name: "HC", lat: 20.68, lon: -103.34 }),
  { requester_name: "Familia", blood_type: "A+", units_needed: 2, urgency: "critica", hours_valid: 12,
    hospital_name: "HC", hospital_lat: 20.68, hospital_lon: -103.34 }));
```

```js
// tests/web/session.test.mjs
const memoryStorage = () => { const m = new Map();
  return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, v), removeItem: k => m.delete(k) }; };
test("guarda, lee y borra", () => { const s = createSession(memoryStorage());
  assert.equal(s.get(), null); s.set("abc"); assert.equal(s.get(), "abc"); s.clear(); assert.equal(s.get(), null); });
test("404 cierra la sesión", () => { assert.equal(sessionAfterError(404), "clear");
  assert.equal(sessionAfterError(409), "keep"); });
```

- [ ] **Step 2: Run** — `node --test tests/web/` → FAIL.
- [ ] **Step 3: Implement** — `errorMessage` usa el último elemento de `loc` y une con `". "`; sin detalle: `>= 500` → `"Error del servidor (N)"`, otro → `"Error (N)"`. Los payloads convierten con `Number(...)` y omiten valores `""`.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(web): módulos de formato, payloads, catálogos y sesión"`

---

### Task 7: Cliente HTTP

**Files:** Create `src/donacion/web/static/js/api.js`; Test `tests/web/api.test.mjs`

**Interfaces:**
- Consumes: `errorMessage` (Task 6).
- Produces: `class ApiError extends Error { status }`; `createApi(fetchImpl = globalThis.fetch)` → `{registerDonor(p), login(email, password), getDonor(id), submitScreening(id, p), getAlerts(id), createRequest(p), getRequest(id), getCandidates(id), dispatch(id), confirm(requestId, donorId), escalate(), health()}`; cada uno devuelve el JSON o lanza `ApiError`. Rutas y métodos: tabla de endpoints del README.

- [ ] **Step 1: Write the failing test**

```js
const fakeFetch = (status, body) => { const calls = [];
  return { calls, impl: async (url, init) => { calls.push({ url, init });
    return { ok: status < 400, status, json: async () => body }; } }; };
test("POST con JSON", async () => { const f = fakeFetch(200, { id: "r1" });
  assert.deepEqual(await createApi(f.impl).confirm("r1", "d9"), { id: "r1" });
  assert.equal(f.calls[0].url, "/requests/r1/confirm"); assert.equal(f.calls[0].init.method, "POST");
  assert.equal(f.calls[0].init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { donor_id: "d9" }); });
test("errores → ApiError legible", async () => { const f = fakeFetch(409, { detail: "La solicitud está cubierta" });
  await assert.rejects(createApi(f.impl).dispatch("r1"),
    e => e instanceof ApiError && e.status === 409 && e.message === "La solicitud está cubierta"); });
test("GET sin cuerpo", async () => { const f = fakeFetch(200, []);
  await createApi(f.impl).getCandidates("r1");
  assert.equal(f.calls[0].init.method, "GET"); assert.equal(f.calls[0].init.body, undefined); });
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** con un helper interno `request(method, path, body?)`; si `!ok`, lee `json()` (si falla, `{}`) y lanza `ApiError(errorMessage(data.detail, status), status)`. **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(web): cliente HTTP"`

---

### Task 8: Página del donante

**Files:** Create `src/donacion/web/static/donante.html`, `src/donacion/web/static/js/donante.js`; Modify `tests/test_web.py`

**Interfaces:**
- Consumes: Tasks 6 y 7.
- Produces (ids fijados por la prueba): `form-registro`, `form-acceso`, `seccion-perfil`, `perfil-nombre`, `perfil-tipo`, `perfil-estado`, `form-tamizaje`, `lista-alertas`, `btn-salir`, `mensaje`. `<select name="zone">` se llena con `ZONES`; `<select name="blood_type">` con los 8 tipos.

Comportamiento: sin sesión se ven registro y acceso; con sesión, perfil (`.insignia-<estado>` + `eligibilityText`), cuestionario y alertas. Registro o acceso guardan el `donorId`. Enviar el cuestionario actualiza la insignia. Cada alerta muestra su mensaje y el botón **"Confirmo que voy a donar"** → `confirm(alert.request_id, donorId)` y recarga perfil y alertas. Hay un botón **Actualizar** para las alertas. Los errores van en `#mensaje.error`; si `sessionAfterError(e.status) === "clear"`, se cierra la sesión.

- [ ] **Step 1: Failing test**

```python
DONANTE_IDS = ["form-registro", "form-acceso", "seccion-perfil", "perfil-nombre", "perfil-tipo",
               "perfil-estado", "form-tamizaje", "lista-alertas", "btn-salir", "mensaje"]
def test_pagina_donante_tiene_los_elementos_que_usa_su_script():
    html = client().get("/app/donante.html").text
    for element_id in DONANTE_IDS: assert f'id="{element_id}"' in html, element_id
    assert 'src="js/donante.js"' in html and 'type="module"' in html
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — `pytest -q` y `node --test tests/web/` → PASS.
- [ ] **Step 5: Verificación manual** en `http://localhost:8000/app/donante.html` (con `python run.py`):
  1. Registrar a Mariana Torres, A+, Centro GDL → insignia "Pendiente".
  2. Enviar el cuestionario vacío → "Apto"; con tatuaje `2026-09-01` → "Diferido … desde el 2027-09-01".
  3. Registrarse con `donante1@demo.mx` → "Ya existe un donante con ese correo".
  4. Dejar vacía la fecha de nacimiento → mensaje legible.
  5. Reiniciar el servidor y recargar → vuelve al acceso.
  6. Revisar que los colores sean solo blanco y rojo pastel.
- [ ] **Step 6: Commit** — `git commit -m "feat(web): página del donante"`

---

### Task 9: Página de la solicitud + README

**Files:** Create `src/donacion/web/static/solicitud.html`, `src/donacion/web/static/js/solicitud.js`; Modify `tests/test_web.py`, `README.md`

**Interfaces:**
- Consumes: Tasks 6 y 7.
- Produces (ids): `form-solicitud`, `seccion-estado`, `estado-resumen`, `tabla-candidatos`, `btn-candidatos`, `btn-oleada`, `btn-escalar`, `lista-oleadas`, `mensaje`, `indicador-ia`. Solicitud activa en `localStorage` clave `"donacion.requestId"`.

Comportamiento: `#indicador-ia` dice "Agente con IA (Claude)" o "Agente con reglas" (según `health().agente_con_ia`). Crear la solicitud: hospital de `HOSPITALS`, urgencia en `<select>` con `urgencyLabel`, vigencia en horas (24 por defecto). El estado muestra tipo, unidades confirmadas/necesarias, urgencia, `statusLabel` y oleadas. **Ver candidatos** llena la tabla: posición, nombre, tipo, puntaje, km y razones. **Enviar oleada** muestra `describeDispatch` y los mensajes agrupados por oleada. **Revisar escalamiento**: si no hubo nada para esta solicitud, muestra "Aún no toca otra oleada (espera de 15 minutos)". Si la solicitud está cubierta o vencida, se deshabilitan los botones de oleada. **Nueva solicitud** borra el id guardado.

- [ ] **Step 1: Failing test**

```python
SOLICITUD_IDS = ["form-solicitud", "seccion-estado", "estado-resumen", "tabla-candidatos", "btn-candidatos",
                 "btn-oleada", "btn-escalar", "lista-oleadas", "mensaje", "indicador-ia"]
def test_pagina_solicitud_tiene_los_elementos_que_usa_su_script():
    html = client().get("/app/solicitud.html").text
    for element_id in SOLICITUD_IDS: assert f'id="{element_id}"' in html, element_id
    assert 'src="js/solicitud.js"' in html and 'type="module"' in html
```

- [ ] **Step 2: Run** — FAIL. **Step 3: Implement.** **Step 4: Run** — PASS.
- [ ] **Step 5: Verificación manual del flujo de la demo** en `http://localhost:8000`:
  1. Solicitud: Familia Pérez, A+, 2 unidades, Hospital Civil Fray Antonio Alcalde, crítica → "Abierta 0/2".
  2. Ver candidatos → no aparecen Gabriela Paz, Héctor Luna, Jorge Ríos ni Fernando Gil.
  3. Enviar oleada → "Oleada 1 enviada a N donantes."
  4. En otra pestaña, entrar a `donante.html` como `donante1@demo.mx` / `demo1234` (Ana López) → "Confirmo que voy a donar"; repetir con otro donante que recibió la alerta → "Cubierta 2/2" y los botones de oleada deshabilitados.
- [ ] **Step 6: README** — sección "Interfaz web": `python run.py` → `http://localhost:8000`; qué hace cada página; el flujo de la demo; aviso de que la sesión es `localStorage` (MVP sin tokens); `node --test tests/web/`.
- [ ] **Step 7: Commit** — `git commit -m "feat(web): página de solicitud y documentación"`
