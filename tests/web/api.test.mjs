import test from "node:test";
import assert from "node:assert/strict";
import { createApi, ApiError } from "../../src/donacion/web/static/js/api.js";

const fakeFetch = (status, body) => {
  const calls = [];
  return { calls, impl: async (url, init) => {
    calls.push({ url, init });
    return { ok: status < 400, status, json: async () => body };
  } };
};

test("POST con JSON", async () => {
  const f = fakeFetch(200, { id: "r1" });
  assert.deepEqual(await createApi(f.impl).confirm("r1", "d9"), { id: "r1" });
  assert.equal(f.calls[0].url, "/requests/r1/confirm");
  assert.equal(f.calls[0].init.method, "POST");
  assert.equal(f.calls[0].init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { donor_id: "d9" });
});

test("errores → ApiError legible", async () => {
  const f = fakeFetch(409, { detail: "La solicitud está cubierta" });
  await assert.rejects(createApi(f.impl).dispatch("r1"),
    e => e instanceof ApiError && e.status === 409 && e.message === "La solicitud está cubierta");
});

test("GET sin cuerpo", async () => {
  const f = fakeFetch(200, []);
  await createApi(f.impl).getCandidates("r1");
  assert.equal(f.calls[0].url, "/requests/r1/candidates");
  assert.equal(f.calls[0].init.method, "GET");
  assert.equal(f.calls[0].init.body, undefined);
});

test("rutas de todos los endpoints", async () => {
  const f = fakeFetch(200, {});
  const api = createApi(f.impl);
  await api.registerDonor({}); await api.login("a@a.mx", "x"); await api.getDonor("d1");
  await api.submitScreening("d1", {}); await api.getAlerts("d1"); await api.createRequest({});
  await api.getRequest("r1"); await api.escalate(); await api.health();
  assert.deepEqual(f.calls.map(c => `${c.init.method} ${c.url}`), [
    "POST /donors", "POST /auth/login", "GET /donors/d1", "POST /donors/d1/screening",
    "GET /donors/d1/alerts", "POST /requests", "GET /requests/r1", "POST /requests/escalate", "GET /health"]);
});

test("error sin JSON usa el código", async () => {
  const impl = async () => ({ ok: false, status: 500, json: async () => { throw new Error("no json"); } });
  await assert.rejects(createApi(impl).health(), e => e.status === 500 && e.message === "Error del servidor (500)");
});
