# Plataforma Agéntica de Donación de Sangre – MVP

Primera versión del proyecto de Diseño de Software (ITESO), basada en el documento
[Visión y Alcances v2](docs/vision_y_alcances_v2.pdf). Se alinea con el **ODS 3: Salud y Bienestar**.

**Autora:** Maria Rebeca Armenta Armenta

## Qué incluye este MVP

| # | Característica | Qué hace |
|---|---|---|
| 1 | Registro y perfil del donante | Registro con contraseña cifrada, inicio de sesión y perfil (tipo de sangre, peso, ubicación, última donación). |
| 2 | Cuestionario de tamizaje | Reglas fijas basadas en la NOM-253-SSA1-2012: edad, peso, tatuajes, cirugías, medicamentos, intervalo entre donaciones y exclusiones permanentes. Resultado: **apto**, **diferido** (con la fecha en que vuelve a ser apto) o **no apto**. |
| 3 | Solicitud de sangre | Un familiar registra tipo de sangre, unidades, hospital, urgencia y vigencia. |
| 4 | Agente de priorización y matching | Filtra donantes compatibles (ABO/Rh), aptos y cercanos; los **ordena** con un puntaje (distancia, compatibilidad, tasa de respuesta, reserva de O-); avisa **por oleadas** de 10 y, si en 15 minutos no se cubre la solicitud, envía la siguiente; **explica** cada alerta. |

Fuera del MVP (versiones posteriores): validación por banco de sangre, historial de donaciones
y recordatorios. Mapa de campañas y estadísticas regionales **no se desarrollan**.

### ¿Qué razona el agente?

1. **Filtra** con reglas duras: compatibilidad ABO/Rh, elegibilidad médica y distancia máxima (50 km).
2. **Prioriza** a los candidatos. Con IA, Claude reordena a los mejores 15 según la urgencia,
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
adapters/     implementaciones: memoria, consola, Claude, PBKDF2, reloj
container.py  composition root: elige la fábrica del agente y arma la fachada DonationPlatform
```

Las dependencias apuntan hacia adentro: el dominio no conoce FastAPI, la base de datos ni la IA.

Documentación de diseño:
- [docs/patrones_y_solid.md](docs/patrones_y_solid.md): dónde está cada principio SOLID y cada patrón (Factory Method, Facade, Adapter, Strategy, Template Method, Repository).
- [docs/refactorizacion.md](docs/refactorizacion.md): bitácora de refactorizaciones (olor de código → técnica → antes/después → commit).
- [docs/diagrama_clases.md](docs/diagrama_clases.md): diagrama de clases.

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

**Demo en consola** (registro → tamizaje → solicitud → ranking → oleada → confirmación):

```bash
python scripts/demo_cli.py
```

**Pruebas:**

```bash
python -m pytest
```

### Usar la IA (Claude)

El agente usa **Claude Opus 5.5** mediante la SDK oficial `anthropic`. Se activa solo si hay credenciales:

```bash
export ANTHROPIC_API_KEY="tu-clave"     # Windows: set ANTHROPIC_API_KEY=tu-clave
```

- `DONACION_USE_LLM=0` fuerza el modo solo reglas; `DONACION_USE_LLM=1` lo fuerza con IA.
- Sin clave, todo funciona con reglas. `GET /health` indica si el agente usa IA.
- Al modelo solo se le envían datos necesarios para decidir (tipo de sangre, distancia, tasa de respuesta); nunca nombres, correos ni ubicación exacta.
- `DONACION_SEED_DEMO=0` arranca la API sin datos de prueba.

## Endpoints

| Método | Ruta | Característica |
|---|---|---|
| POST | `/donors` | Registrar donante |
| POST | `/auth/login` | Iniciar sesión |
| GET | `/donors`, `/donors/{id}` | Consultar perfil y elegibilidad |
| GET | `/donors/{id}/alerts` | Alertas recibidas por el donante |
| POST | `/donors/{id}/screening` | Contestar el cuestionario de tamizaje |
| POST | `/requests` | Crear solicitud de sangre |
| GET | `/requests/{id}` | Estado de la solicitud |
| GET | `/requests/{id}/candidates` | Orden que propone el agente (sin enviar) |
| POST | `/requests/{id}/dispatch` | Enviar la siguiente oleada de alertas |
| POST | `/requests/{id}/confirm` | Un donante confirma su donación |
| POST | `/requests/escalate` | Enviar nueva oleada a solicitudes no cubiertas a tiempo |

## Datos de prueba

`src/donacion/demo.py` carga 12 donantes ficticios en Guadalajara (contraseña `demo1234`,
correos `donante1@demo.mx` a `donante12@demo.mx`). Incluye casos para la demo: una donante con tatuaje
reciente (diferida), uno que donó hace 30 días (diferido), uno con peso menor a 50 kg (no apto),
una donante O- (reservada si la urgencia no es crítica) y tipos incompatibles.

> Los plazos del tamizaje (12 meses por tatuaje, 6 por cirugía, 5 días por medicamento, 56 días entre
> donaciones) son configurables en `container.py` y deben verificarse contra la NOM-253 vigente.
