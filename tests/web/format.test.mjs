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

import { describeEscalation } from "../../src/donacion/web/static/js/format.js";

test("escalamiento: distingue esperar, sin primera oleada y sin donantes", () => {
  const request = (waves, notified) => ({ waves_sent: waves, notified_donors: notified });
  const cand = ids => ids.map(id => ({ donor_id: id }));
  assert.equal(describeEscalation([{ wave: 2 }], request(1, ["a"]), cand(["a", "b"])), "Oleada 2 enviada a 1 donante.");
  assert.equal(describeEscalation([], request(0, []), cand(["a"])), "Primero envía la primera oleada de alertas.");
  assert.equal(describeEscalation([], request(1, ["a", "b"]), cand(["a", "b"])),
    "Ya no quedan donantes compatibles por avisar.");
  assert.equal(describeEscalation([], request(1, ["a"]), cand(["a", "b"])),
    "Aún no toca otra oleada (espera de 15 minutos).");
});
