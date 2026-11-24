import test from "node:test";
import assert from "node:assert/strict";
import { buildDonorPayload, buildProfilePayload, buildScreeningPayload, buildRequestPayload } from "../../src/donacion/web/static/js/payloads.js";
import { ZONES } from "../../src/donacion/web/static/js/catalogs.js";

test("donante: números y sin última donación vacía", () => assert.deepEqual(
  buildDonorPayload({ name: "Ana", email: "a@a.mx", password: "segura123", birth_date: "2000-01-02",
    weight_kg: "61.5", blood_type: "O+", last_donation: "" }, { lat: 20.67, lon: -103.34 }),
  { name: "Ana", email: "a@a.mx", password: "segura123", birth_date: "2000-01-02", weight_kg: 61.5,
    blood_type: "O+", lat: 20.67, lon: -103.34 }));
test("tamizaje: omite fechas vacías", () => assert.deepEqual(
  buildScreeningPayload({ tattoo_or_piercing_date: "", surgery_date: "2026-10-01", medication_end_date: "",
    permanent_exclusion: false }), { surgery_date: "2026-10-01", permanent_exclusion: false }));
test("solicitud solo manda el id del hospital del catálogo", () => assert.deepEqual(
  buildRequestPayload({ requester_name: "Familia", blood_type: "A+", units_needed: "2", urgency: "critica",
    hours_valid: "12", hospital: "hc-fray-antonio" }),
  { requester_name: "Familia", blood_type: "A+", units_needed: 2, urgency: "critica", hours_valid: 12,
    hospital_id: "hc-fray-antonio" }));
test("perfil: manda lo editable y omite la zona si no cambia", () => {
  assert.deepEqual(
    buildProfilePayload({ name: "Ana", weight_kg: "58.5", zone: "", last_donation: "" }, undefined),
    { name: "Ana", weight_kg: 58.5 });
  assert.deepEqual(
    buildProfilePayload({ name: "Ana", weight_kg: "58", zone: "zapopan", last_donation: "2026-09-01" },
      { lat: 20.72, lon: -103.39 }),
    { name: "Ana", weight_kg: 58, lat: 20.72, lon: -103.39, last_donation: "2026-09-01" });
});
test("zonas con coordenadas", () => {
  assert.equal(ZONES.length, 6);
  for (const item of ZONES) assert.ok(item.id && item.name && item.lat && item.lon);
});
