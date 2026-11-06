import test from "node:test";
import assert from "node:assert/strict";
import { buildDonorPayload, buildScreeningPayload, buildRequestPayload } from "../../src/donacion/web/static/js/payloads.js";
import { ZONES, HOSPITALS } from "../../src/donacion/web/static/js/catalogs.js";

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
test("catálogos con coordenadas", () => {
  assert.equal(ZONES.length, 6);
  assert.deepEqual(HOSPITALS[0], { id: "hc-fray-antonio", name: "Hospital Civil Fray Antonio Alcalde",
    lat: 20.6866, lon: -103.3496 });
  for (const item of [...ZONES, ...HOSPITALS]) assert.ok(item.id && item.name && item.lat && item.lon);
});
