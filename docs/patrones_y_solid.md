# Programación orientada a objetos, SOLID y patrones

Este documento señala **dónde** está en el código cada concepto visto en clase y **por qué** se usó.
Todas las rutas son relativas a `src/donacion/`.

---

## Pilares de la POO

### Encapsulamiento
Los atributos de las entidades son privados (prefijo `_`) y solo cambian a través de métodos que validan las reglas.

- `domain/blood_request.py` → `BloodRequest`: `confirm_unit()` impide confirmar dos veces, confirmar sin haber recibido la alerta o confirmar una solicitud cerrada. Nadie puede escribir `units_confirmed = -3`.
- `domain/donor.py` → `Donor`: la elegibilidad solo cambia con `update_eligibility()` o `record_donation()`.

### Herencia
- `screening/rules.py` → `TattooRule`, `SurgeryRule`, `MedicationRule` y `DonationIntervalRule` heredan de `_WaitingPeriodRule`, que a su vez hereda de `EligibilityRule`.
- `agent/factory.py` → `RuleBasedAgentFactory` y `AIAgentFactory` heredan de `MatchingAgentFactory`.

### Polimorfismo
- `screening/evaluator.py` → `ScreeningEvaluator.evaluate()` recorre una lista de `EligibilityRule` y llama a `rule.evaluate(...)` sin saber qué regla es cada una.
- `agent/matching_agent.py` → `MatchingAgent` llama a `scoring.rank(...)` sin saber si detrás hay reglas o IA.

### Abstracción
Los puertos en `ports/` son clases abstractas (`ABC`) que definen **qué** se necesita sin decir **cómo**: `DonorRepository`, `RequestRepository`, `Notifier`, `AlertLog`, `LLMClient`, `PasswordHasher`, `Clock` e `IdGenerator`.

---

## Principios SOLID

### S — Responsabilidad única
Cada clase tiene una sola razón para cambiar.

- Cada regla de la NOM-253 es una clase: `AgeRule`, `WeightRule`, `TattooRule`… (`screening/rules.py`).
- `MatchingAgent` decide, `MatchingService` coordina y guarda, `Notifier` envía y `AlertLog` recuerda.
- Confirmar una donación: `RequestService.confirm_unit()` solo cuenta la unidad en la solicitud y `DonorService.record_donation()` solo difiere al donante; la fachada `DonationPlatform.confirm_donation()` coordina ambos. Antes `RequestService` hacía las dos cosas y guardaba en dos repositorios.
- `AuthService` abre la sesión y reconoce al donante por su token; `HospitalCatalog` es la única fuente de los hospitales.
- Refactorizaciones que aplicaron SRP: `ResponseHistory` salió de `Donor`; `RerankPromptBuilder` y `ExplanationPromptBuilder` salieron de las estrategias de IA; `AlertLog` salió de `ConsoleNotifier` (ver `refactorizacion.md`).

### O — Abierto/cerrado
El sistema se extiende agregando clases, no modificando las existentes.

- Una regla clínica nueva = una clase `EligibilityRule` nueva registrada en `container.py`; `ScreeningEvaluator` no cambia.
- Una forma nueva de priorizar = otra fábrica concreta de `MatchingAgentFactory` (`agent/factory.py`); `MatchingAgent` no cambia.
- Un filtro nuevo = otra clase `CandidateFilter` (`agent/filters.py`).

### L — Sustitución de Liskov
Cualquier subclase puede usarse donde se espera la clase base sin romper nada.

- `RuleBasedScoring` y `LLMAssistedScoring` son intercambiables como `ScoringStrategy`; `TemplateExplanation` y `LLMExplanation` como `ExplanationBuilder`.
- Prueba: `tests/test_factory_facade.py::test_las_fabricas_son_intercambiables` usa las dos fábricas en el mismo código y obtiene el mismo resultado.
- Esto hace posible la tolerancia a fallos: si la IA falla, se usa la implementación por reglas en su lugar.
- Repositorios: `tests/test_sqlite.py` corre **las mismas pruebas de contrato** contra la versión en memoria y contra SQLite; las dos pasan igual, así que una sustituye a la otra.

### I — Segregación de interfaces
Las interfaces son pequeñas y específicas en lugar de un "DataManager" gigante: `DonorRepository`, `RequestRepository`, `Notifier` (solo `send`), `AlertLog`, `LLMClient` (solo `complete_json`), `Clock` (solo `now`) e `IdGenerator` (solo `new_id`).

### D — Inversión de dependencias
Los módulos de alto nivel dependen de abstracciones, no de clases concretas.

- Los servicios (`services/`) reciben puertos en su constructor; nunca crean adaptadores.
- `api/routes.py` depende solo de la fachada `DonationPlatform` (lo comprueba `test_la_api_solo_depende_de_la_fachada`).
- `container.py` es el único lugar que conoce las clases concretas (*composition root*).
- Refactorización aplicada: la ruta de alertas dependía de `ConsoleNotifier.sent_to()` (clase concreta); ahora depende del puerto `AlertLog`.

---

## Patrones de diseño

### Factory Method — `agent/factory.py`
Misma estructura que el ejemplo de clase (`Mundo` → `ModoCreativo`):

| Parte del patrón | En clase | En el proyecto |
|---|---|---|
| Interfaz de producto | `Bloque` | `ScoringStrategy`, `ExplanationBuilder` |
| Productos concretos | `Piedra`, `Pasto`… | `RuleBasedScoring`, `LLMAssistedScoring`, `TemplateExplanation`, `LLMExplanation` |
| Clase creadora con método fábrica | `Mundo.crear_bloque()` | `MatchingAgentFactory.create_scoring()` y `create_explainer()` |
| Operación que usa el método fábrica | `Mundo.colocar()` | `MatchingAgentFactory.build()` |
| Fábricas concretas | `ModoCreativo`… | `RuleBasedAgentFactory`, `AIAgentFactory` |

**Por qué:** el sistema debe funcionar con IA o sin ella (tolerancia a fallos). `container.py` elige la fábrica una sola vez y el resto del código nunca pregunta "¿hay IA?".

### Facade — `services/platform.py`
`DonationPlatform` ofrece una sola interfaz simple (`register_donor`, `submit_screening`, `create_request_valid_for`, `dispatch_wave`…) que oculta cuatro servicios, el agente, los repositorios y el reloj. La API y la demo en consola solo usan la fachada.

**Diferencia con Adapter:** la fachada **simplifica** un subsistema propio; el adaptador **traduce** una interfaz ajena a la que el sistema espera.

### Adapter — `adapters/`
- `adapters/ollama_llm_client.py` → `OllamaLLMClient` adapta la API HTTP de Ollama (modelo local) al puerto `LLMClient`. Si se cambia de modelo o de servidor de IA, solo cambia este archivo.
- `adapters/memory_repositories.py`, `pbkdf2_hasher.py`, `hmac_tokens.py`, `system_clock.py`, `uuid_ids.py` adaptan almacenamiento, cifrado, tokens de sesión, reloj e identificadores a sus puertos.

### Strategy — `agent/scoring.py`, `agent/explanation.py`
Familias de algoritmos intercambiables: cómo ordenar candidatos y cómo redactar alertas. El agente recibe la estrategia y no sabe cuál es.

### Template Method — `screening/rules.py`, `agent/factory.py`
- `_WaitingPeriodRule.evaluate()` define el algoritmo "si hubo un evento, esperar hasta cierta fecha"; las subclases solo implementan `_event_date()` y `_until()`.
- `MatchingAgentFactory.build()` define cómo se arma el agente; las subclases deciden las piezas.

### Decorator — `adapters/retrying_notifier.py`
`RetryingNotifier` implementa `Notifier` y envuelve a otro `Notifier` para agregarle reintentos con espera creciente. Ni `ConsoleNotifier` ni `MatchingService` cambian; el contenedor decide si se envuelve.

### Repository — `ports/repositories.py`
El dominio guarda y busca entidades a través de una interfaz. La app usa SQLite (`adapters/sqlite_repositories.py`: `SqliteDonorRepository`, `SqliteRequestRepository`, `SqliteAlertLog`) y existen también las versiones en memoria; los servicios no saben cuál reciben. Las entidades se reconstruyen con su método de clase `restore()`, así el repositorio no rompe su encapsulamiento.

### Inyección de dependencias + Composition Root — `container.py`
Todas las dependencias se pasan por constructor. `PlatformBuilder` arma el sistema completo en un solo lugar a partir de un objeto `Settings` (`config.py`), que es la única clase que lee variables de entorno y las valida al arrancar. Ninguna otra clase llama a `os.getenv`.

### Value Object (DDD)
Objetos inmutables definidos por su valor: `BloodType`, `Location`, `EligibilityResult`, `ResponseHistory`, `ScoringWeights`, `Alert` (`@dataclass(frozen=True)`).
