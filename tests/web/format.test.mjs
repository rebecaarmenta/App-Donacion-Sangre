import test from "node:test";
import assert from "node:assert/strict";
import { escapeHtml, errorMessage, urgencyLabel, statusLabel, eligibilityText, describeDispatch }
  from "../../src/donacion/web/static/js/format.js";

test("escapa HTML y conserva acentos", () =>
  assert.equal(escapeHtml(`<b>Núñez</b> & "x"`), "&lt;b&gt;Núñez&lt;/b&gt; &amp; &quot;x&quot;"));
test("error de dominio en texto", () =>
  assert.equal(errorMessage("Ya existe un donante con ese correo", 409), "Ya existe un donante con ese correo"));
test("error 422 en lista se vuelve legible", () => assert.equal(
  errorMessage([{ loc: ["body", "birth_date"], msg: "Input should be a valid date" },
                { loc: ["body", "weight_kg"], msg: "Input should be greater than 0" }], 422),
  "birth_date: Input should be a valid date. weight_kg: Input should be greater than 0"));
test("sin detalle usa el código", () => {
  assert.equal(errorMessage(undefined, 500), "Error del servidor (500)");
  assert.equal(errorMessage(undefined, 418), "Error (418)");
});
test("etiquetas", () => {
  assert.equal(urgencyLabel("critica"), "crítica");
  assert.equal(statusLabel("no_apto"), "No apto");
  assert.equal(statusLabel("cubierta"), "Cubierta");
  assert.equal(statusLabel("raro"), "raro");
});
test("elegibilidad diferida con fecha", () => assert.equal(
  eligibilityText({ status: "diferido", reasons: ["Tatuaje"], eligible_from: "2027-08-06" }),
  "Diferido: Tatuaje. Podrás donar desde el 2027-08-06."));
test("elegibilidad apta sin fecha", () => assert.equal(
  eligibilityText({ status: "apto", reasons: ["Cumple todos los requisitos"], eligible_from: null }),
  "Apto: Cumple todos los requisitos."));
test("oleadas", () => {
  assert.equal(describeDispatch([]), "Ya no quedan donantes compatibles por avisar.");
  assert.equal(describeDispatch([{ wave: 2 }, { wave: 2 }]), "Oleada 2 enviada a 2 donantes.");
  assert.equal(describeDispatch([{ wave: 1 }]), "Oleada 1 enviada a 1 donante.");
});

import { describeCreated, describeImpact, describeProfileSaved } from "../../src/donacion/web/static/js/format.js";

test("perfil guardado: solo pide repetir el cuestionario si el cambio lo invalidó", () => {
  const status = s => ({ eligibility: { status: s } });
  const repetir = { text: "Guardamos tus cambios. Como cambiaste tu peso o tu última donación, contesta de nuevo el cuestionario.", kind: "error" };
  const ok = { text: "Guardamos tus cambios.", kind: "ok" };
  assert.deepEqual(describeProfileSaved(status("apto"), status("pendiente")), repetir);
  assert.deepEqual(describeProfileSaved(status("diferido"), status("pendiente")), repetir);
  // una cuenta nueva ya estaba pendiente: cambiar su nombre o zona no es "cambiaste tu peso"
  assert.deepEqual(describeProfileSaved(status("pendiente"), status("pendiente")), ok);
  assert.deepEqual(describeProfileSaved(status("apto"), status("apto")), ok);
  assert.deepEqual(describeProfileSaved(null, status("pendiente")), ok);
});

test("impacto: cuenta donaciones y solicitudes cubiertas", () => {
  assert.equal(describeImpact({ total: 0, requests_covered: 0 }), "Aún no tienes donaciones registradas en la app.");
  assert.equal(describeImpact({ total: 1, requests_covered: 0 }), "Has donado 1 vez.");
  assert.equal(describeImpact({ total: 3, requests_covered: 2 }),
    "Has donado 3 veces y ayudaste a cubrir 2 solicitudes.");
  assert.equal(describeImpact({ total: 2, requests_covered: 1 }),
    "Has donado 2 veces y ayudaste a cubrir 1 solicitud.");
});

test("al crear: dice a cuántos avisó o que no hubo a quién", () => {
  assert.equal(describeCreated({ notified_donors: ["a", "b"] }),
    "Solicitud creada. El agente ya avisó a 2 donantes (oleada 1).");
  assert.equal(describeCreated({ notified_donors: ["a"] }),
    "Solicitud creada. El agente ya avisó a 1 donante (oleada 1).");
  assert.equal(describeCreated({ notified_donors: [] }),
    "Solicitud creada, pero no hay donantes compatibles, aptos y cercanos por avisar.");
});
