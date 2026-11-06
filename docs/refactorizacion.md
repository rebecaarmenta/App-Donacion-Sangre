# Bitácora de refactorización

Refactorizar es **mejorar la estructura del código sin cambiar su comportamiento**. Cada cambio de esta
bitácora se hizo así:

1. Con la suite de pruebas en verde (las 39 pruebas originales del MVP).
2. Primero una prueba nueva que falla (RED) y fija lo que debe cumplir la nueva estructura.
3. El cambio mínimo para que pase (GREEN).
4. La suite completa otra vez en verde y un commit propio (`git log` muestra cada uno).

Las 39 pruebas originales pasaron antes y después de cada refactorización. Los únicos cambios en ellas
fueron de construcción: `tests/test_api.py` pasó de `build_container` a `build_platform` y el doble de prueba
`FakeLLM` se movió a `tests/conftest.py`; ninguna aserción cambió.

---

## 1. Dependencia de una clase concreta → puerto `AlertLog` e `IdGenerator`
**Commit:** `05ff944` · **Técnicas:** Dependency Inversion, Extract Interface, Extract Class

**Olores de código:**
- La ruta `/donors/{id}/alerts` llamaba a `ConsoleNotifier.sent_to()`, un método de la clase concreta. Al cambiar a notificaciones push, la ruta se rompería (viola DIP).
- `ConsoleNotifier` enviaba **y** guardaba alertas (viola SRP).
- `lambda: uuid.uuid4().hex[:8]` estaba copiado en dos servicios (código duplicado).

**Antes:**
```python
# api/routes.py
return [AlertOut.of(a) for a in c.notifier.sent_to(donor_id)]
# services/donor_service.py y request_service.py
id_factory: Callable[[], str] = lambda: uuid.uuid4().hex[:8]
```

**Después:**
```python
# ports/alert_log.py
class AlertLog(ABC):
    def record(self, alert: Alert) -> None: ...
    def for_donor(self, donor_id: str) -> list[Alert]: ...
# services/matching_service.py
self._notifier.send(alert)
self._alert_log.record(alert)
```

**Pruebas:** `test_las_alertas_se_registran_en_el_log_y_no_en_el_notificador`, `test_ids_inyectados`, `test_console_notifier_solo_envia`.

---

## 2. `Donor` con dos responsabilidades → `ResponseHistory`
**Commit:** `433bb83` · **Técnica:** Extract Class (value object inmutable)

**Olor de código:** `Donor` manejaba el perfil **y** contadores de respuesta a alertas (viola SRP).

**Antes:**
```python
self._alerts_received = 0
self._alerts_accepted = 0
...
self._alerts_received += 1
```

**Después:**
```python
self._history = ResponseHistory()
...
self._history = self._history.with_alert()
```

**Pruebas:** `test_historial_de_respuesta_es_inmutable_y_calcula_la_tasa`, `test_donante_expone_su_historial`.

---

## 3. Números mágicos → `ScoringWeights`
**Commit:** `1583e0b` · **Técnicas:** Replace Magic Number with Symbolic Constant, Introduce Parameter Object

**Olor de código:** los pesos del puntaje estaban escritos dentro del cálculo; para ajustarlos había que modificar la estrategia.

**Antes:**
```python
score = 45 * proximity + 25 * (1.0 if exact_match else 0.6) + 30 * donor.response_rate
score -= 20
```

**Después:**
```python
match = 1.0 if exact_match else self._w.compatible_factor
score = (self._w.proximity * proximity + self._w.blood_match * match
         + self._w.response * donor.response_rate)
score -= self._w.universal_reserve_penalty
```

**Pruebas:** `test_pesos_por_defecto_conservan_el_orden` (fija los puntajes calculados con el código anterior, commit `1dcef3f`; si cambia un peso por defecto, falla) y `test_pesos_configurables_cambian_la_prioridad`.

---

## 4. Estrategias de IA que también arman prompts → constructores de prompts
**Commit:** `1e8eb69` · **Técnicas:** Extract Class, Move Method

**Olor de código:** `LLMAssistedScoring` y `LLMExplanation` decidían **y** armaban el texto para el modelo (viola SRP). La regla de privacidad (no enviar nombres ni correos) estaba repartida.

**Antes:**
```python
reply = self._llm.complete_json(_RERANK_SYSTEM, self._prompt(head, request), _RERANK_SCHEMA)
```

**Después:**
```python
reply = self._llm.complete_json(self._prompts.system, self._prompts.build(head, request),
                                self._prompts.schema)
```

**Pruebas:** `test_prompt_de_orden_no_envia_datos_personales`, `test_prompt_de_explicacion_incluye_razones_sin_correo`.

---

## 5. Búsqueda de solicitudes duplicada → `RequestFinder`
**Commit:** `ed4cfef` · **Técnicas:** Extract Class, eliminar código duplicado (DRY)

**Olor de código:** `RequestService.get()` y `MatchingService._get_open()` repetían "buscar, marcar como vencida, validar".

**Antes (en los dos servicios):**
```python
request = self._requests.get(request_id)
if request is None:
    raise NotFoundError(...)
request.expire_if_needed(self._clock.now())
```

**Después:**
```python
request = self._finder.get_open(request_id)
```

**Prueba:** `test_request_finder_vence_y_rechaza_cerradas`.

---

## Después de refactorizar: patrones
Con el código limpio se agregaron dos patrones (ver `patrones_y_solid.md`):

- `4b13989` — **Factory Method** para construir el agente (`agent/factory.py`).
- `a3a0eda` — **Facade** `DonationPlatform` como única entrada de la API (`services/platform.py`).
- `de24a88` — la API importa también los comandos (`RegisterDonorCommand`) desde la fachada, no desde un servicio.
