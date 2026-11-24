# Plataforma Agéntica de Donación de Sangre

Proyecto de Diseño de Software (ITESO), basado en el documento
[Visión y Alcances v2](docs/vision_y_alcances_v2.pdf). Se alinea con el **ODS 3: Salud y Bienestar**.

**Autora:** Maria Rebeca Armenta Armenta

## Qué incluye la app

| # | Característica | Qué hace |
|---|---|---|
| 1 | Registro y perfil del donante | Registro con contraseña cifrada, inicio de sesión y perfil editable (nombre, peso, ubicación, última donación). |
| 2 | Cuestionario de tamizaje | Reglas fijas basadas en la NOM-253-SSA1-2012: edad, peso, tatuajes, cirugías, medicamentos, intervalo entre donaciones y exclusiones permanentes. Resultado: **apto**, **diferido** (con la fecha en que vuelve a ser apto) o **no apto**. |
| 3 | Solicitud de sangre | Un familiar registra tipo de sangre, unidades, hospital, urgencia y vigencia. |
| 4 | Agente de priorización y matching | Filtra donantes compatibles (ABO/Rh), aptos y cercanos; los **ordena** con un puntaje (distancia, compatibilidad, tasa de respuesta, reserva de O-); avisa **por oleadas** de 10 y, si en 15 minutos no se cubre la solicitud, envía la siguiente; **explica** cada alerta. |
| 5 | Historial de donaciones | Cada donación confirmada queda en el historial del donante, con fecha y hospital, y muestra su impacto: cuántas veces ha donado y cuántas solicitudes ayudó a cubrir. |

Quedan fuera de esta versión la validación de solicitudes por el banco de sangre y los
recordatorios. El historial de donaciones, que estaba planeado para después, ya se incluye.
El mapa de campañas y las estadísticas regionales no forman parte del proyecto.

### ¿Qué razona el agente?

1. **Filtra** con reglas duras: compatibilidad ABO/Rh, elegibilidad médica y distancia máxima (50 km).
2. **Prioriza** a los candidatos. Con IA, un modelo local de Ollama reordena a los mejores 15 según la urgencia,
   la cercanía y la tasa de respuesta, y justifica su decisión.
3. **Planea oleadas** sin repetir donantes y **escala** si la solicitud no se cubre a tiempo.
4. **Explica** a cada donante por qué se le eligió.

La IA **nunca decide si alguien puede donar**: eso lo deciden las reglas del tamizaje.
Si la IA falla o responde algo inválido, el agente usa el orden y los mensajes por reglas
(tolerancia a fallos, sección 7 del documento de visión).

## Arquitectura

```
api/          FastAPI: rutas HTTP y esquemas (solo traduce HTTP <-> servicios)
services/     casos de uso: DonorService, ScreeningService, RequestService, MatchingService
agent/        MatchingAgent + filtros, estrategias de puntaje, oleadas y explicaciones
screening/    reglas de la NOM-253 y ScreeningEvaluator (sin IA)
domain/       entidades y value objects: Donor, BloodRequest, BloodType, Location…
ports/        interfaces: repositorios, Notifier, LLMClient, PasswordHasher, Clock
adapters/     implementaciones: SQLite (y memoria), consola, Ollama, PBKDF2, tokens HMAC, reloj, reintentos, escalamiento
container.py  composition root: elige la fábrica del agente y arma la fachada DonationPlatform
```

Las dependencias apuntan hacia adentro: el dominio no conoce FastAPI, la base de datos ni la IA.

Documentación de diseño:
- [docs/patrones_y_solid.md](docs/patrones_y_solid.md): dónde está cada principio SOLID y cada patrón (Factory Method, Facade, Adapter, Strategy, Template Method, Repository, Decorator).
- [docs/refactorizacion.md](docs/refactorizacion.md): bitácora de refactorizaciones (olor de código → técnica → antes/después → commit).

### Principios SOLID

- **S** – Cada regla de la NOM es una clase (`TattooRule`, `AgeRule`…); el agente decide, el servicio coordina y persiste, el notificador solo envía.
- **O** – Para agregar una regla, un filtro o una estrategia se crea una clase nueva y se registra en `container.py`, sin modificar el evaluador ni el agente.
- **L** – `RuleBasedScoring` y `LLMAssistedScoring` (y `TemplateExplanation` / `LLMExplanation`) son intercambiables.
- **I** – Interfaces pequeñas y separadas: `DonorRepository`, `RequestRepository`, `Notifier`, `LLMClient`, `Clock`.
- **D** – Los servicios reciben interfaces en el constructor; solo `container.py` crea las clases concretas, y la API depende solo de la fachada.

**Patrones:** Factory Method (`agent/factory.py`: `RuleBasedAgentFactory` / `AIAgentFactory`), Facade (`services/platform.py`: `DonationPlatform`), Adapter (`adapters/`), Strategy (puntaje y explicaciones), Template Method (reglas con periodo de espera).

**Encapsulamiento:** los atributos de las entidades son privados y solo cambian con métodos que validan
(`confirm_unit`, `register_wave`, `update_eligibility`, `record_donation`).

## Cómo correrlo

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Aplicación en localhost** (con 12 donantes de prueba ya cargados):

```bash
python run.py
```

Abre http://localhost:8000 en el navegador. La documentación interactiva de la API está en http://localhost:8000/docs.
Para detenerla: `Ctrl + C`.

### Interfaz web

Con `python run.py` abierto, entra a **http://localhost:8000** (redirige a `/app/`).

- **Soy donante** (`/app/donante.html`): registro, inicio de sesión, perfil con su estado (apto, diferido o no apto), cuestionario de elegibilidad y alertas recibidas con el botón "Confirmo que voy a donar".
- **Necesito sangre** (`/app/solicitud.html`): crear la solicitud eligiendo hospital y urgencia, ver las alertas de la primera oleada (se envía sola al crear la solicitud), ver a los candidatos que ordenó el agente con sus razones, adelantar la siguiente oleada y ver el estado (por ejemplo, "Cubierta 2/2"). La página se actualiza cada 10 s.

**Demo en consola** (registro → tamizaje → solicitud → ranking → oleada → confirmación):

```bash
python scripts/demo_cli.py
```

**Pruebas:**

```bash
python -m pytest                       # backend (Python)
node --test tests/web/*.test.mjs       # módulos de la interfaz (JavaScript, Node 18+)
```

### Usar la IA (Ollama)

El agente usa un modelo **local con [Ollama](https://ollama.com)**, así que no hay consumo de tokens de pago. Por defecto usa `llama3.2`:

```bash
ollama pull llama3.2      # una sola vez
ollama serve              # si no está corriendo ya como servicio
```

- `OLLAMA_MODEL` cambia el modelo (por ejemplo `qwen2.5:3b`) y `OLLAMA_HOST` la dirección (`http://localhost:11434` por defecto).
- Si Ollama no está corriendo o responde algo inválido, el agente usa las reglas fijas sin fallar.
- `DONACION_USE_LLM=0` usa solo reglas (por defecto se usa Ollama). `OLLAMA_TIMEOUT_SECONDS` (60 por defecto) es el tiempo máximo de espera por respuesta. `GET /health` indica si el agente usa IA.
- Toda la configuración se lee y valida en `src/donacion/config.py` (`Settings`); un valor inválido detiene el arranque con un mensaje claro.
- Al modelo solo se le envían datos necesarios para decidir (tipo de sangre, distancia, tasa de respuesta); nunca nombres, correos ni ubicación exacta.
- La **primera oleada** siempre se planea con reglas y mensajes de plantilla, para que salga en menos de 5 segundos aunque el modelo local sea lento. La IA reordena y redacta **a partir de la segunda oleada**, que tiene 15 minutos de margen.
- El **escalamiento es automático**: mientras el servidor corre, revisa cada `DONACION_ESCALATION_CHECK_SECONDS` (30 por defecto) si toca otra oleada. `DONACION_AUTO_ESCALATE=0` lo apaga.
- Cada alerta se **reintenta** hasta 3 veces con espera creciente si el canal de notificación falla; aunque se agoten los intentos, la alerta queda visible en la app del donante.
- `DONACION_SEED_DEMO=0` arranca la API sin datos de prueba.
- `DONACION_WAVE_WAIT_MINUTES` cambia la espera entre oleadas (15 minutos por defecto) y `DONACION_WAVE_SIZE` el tamaño de cada oleada (10 por defecto). Para mostrar el escalamiento en una demo con los donantes de prueba:
  `DONACION_WAVE_WAIT_MINUTES=0.25 DONACION_WAVE_SIZE=3 DONACION_ESCALATION_CHECK_SECONDS=5 python run.py` (oleadas de 3 donantes cada 15 segundos).

## Endpoints

| Método | Ruta | Característica |
|---|---|---|
| POST | `/donors` | Registrar donante |
| POST | `/auth/login` | Iniciar sesión (devuelve `access_token`) |
| GET | `/me` 🔒 | Consultar mi perfil y elegibilidad |
| PATCH | `/me` 🔒 | Editar nombre, peso, ubicación o última donación (si cambia el peso o la última donación, hay que repetir el cuestionario) |
| GET | `/me/alerts` 🔒 | Alertas que recibí |
| GET | `/me/donations` 🔒 | Mi historial de donaciones y su impacto |
| POST | `/me/screening` 🔒 | Contestar el cuestionario de tamizaje |
| GET | `/hospitals` | Catálogo de hospitales |
| POST | `/requests` | Crear solicitud de sangre (con `hospital_id` del catálogo); envía la primera oleada y devuelve `manage_token` |
| GET | `/requests/{id}` | Estado de la solicitud |
| GET | `/requests/{id}/candidates` 🔑 | Orden por reglas de los candidatos (sin enviar) |
| POST | `/requests/{id}/dispatch` 🔑 | Adelantar la siguiente oleada de alertas |
| GET | `/requests/{id}/alerts` 🔑 | Alertas enviadas para la solicitud, por oleada |
| POST | `/requests/{id}/confirm` 🔒 | El donante de la sesión confirma su donación |
| POST | `/requests/escalate` | Revisar ahora el escalamiento (el servidor ya lo hace solo) |

🔒 = requiere `Authorization: Bearer <access_token>` (sesión del donante).
🔑 = requiere `X-Request-Token: <manage_token>` (solo quien creó la solicitud; la página lo guarda sola).

