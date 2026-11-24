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
  await createApi(f.impl).createRequest({ hospital_id: "cmno" });
  assert.equal(f.calls[0].init.method, "POST");
  assert.equal(f.calls[0].init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { hospital_id: "cmno" });
});

test("confirmar manda el token y no el id del donante", async () => {
  const f = fakeFetch(200, { id: "r1" });
  assert.deepEqual(await createApi(f.impl, () => "tok.firma").confirm("r1"), { id: "r1" });
  assert.equal(f.calls[0].url, "/requests/r1/confirm");
  assert.equal(f.calls[0].init.headers.Authorization, "Bearer tok.firma");
  assert.equal(f.calls[0].init.body, undefined);
});

test("manejar la solicitud manda su token en X-Request-Token", async () => {
  const f = fakeFetch(200, []);
  const api = createApi(f.impl, () => "sesion-donante");
  await api.getCandidates("r1", "tok-solicitud");
  await api.dispatch("r1", "tok-solicitud");
  await api.getRequestAlerts("r1", "tok-solicitud");
  for (const c of f.calls) assert.equal(c.init.headers["X-Request-Token"], "tok-solicitud");
  assert.deepEqual(f.calls.map(c => `${c.init.method} ${c.url}`),
    ["GET /requests/r1/candidates", "POST /requests/r1/dispatch", "GET /requests/r1/alerts"]);
});

test("historial es GET /me/donations con la sesión", async () => {
  const f = fakeFetch(200, { total: 0, requests_covered: 0, donations: [] });
  await createApi(f.impl, () => "t").getDonations();
  assert.equal(`${f.calls[0].init.method} ${f.calls[0].url}`, "GET /me/donations");
  assert.equal(f.calls[0].init.headers.Authorization, "Bearer t");
});

test("editar perfil es PATCH /me con JSON", async () => {
  const f = fakeFetch(200, {});
  await createApi(f.impl, () => "t").updateProfile({ weight_kg: 60 });
  assert.equal(`${f.calls[0].init.method} ${f.calls[0].url}`, "PATCH /me");
  assert.deepEqual(JSON.parse(f.calls[0].init.body), { weight_kg: 60 });
});

test("sin sesión no manda Authorization", async () => {
  const f = fakeFetch(200, {});
  await createApi(f.impl, () => null).getMe();
  assert.equal(f.calls[0].init.headers.Authorization, undefined);
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
  await api.registerDonor({}); await api.login("a@a.mx", "x"); await api.getMe();
  await api.submitScreening({}); await api.getAlerts(); await api.listHospitals(); await api.createRequest({});
  await api.getRequest("r1"); await api.escalate(); await api.health();
  assert.deepEqual(f.calls.map(c => `${c.init.method} ${c.url}`), [
    "POST /donors", "POST /auth/login", "GET /me", "POST /me/screening",
    "GET /me/alerts", "GET /hospitals", "POST /requests", "GET /requests/r1", "POST /requests/escalate", "GET /health"]);
});

test("error sin JSON usa el código", async () => {
  const impl = async () => ({ ok: false, status: 500, json: async () => { throw new Error("no json"); } });
  await assert.rejects(createApi(impl).health(), e => e.status === 500 && e.message === "Error del servidor (500)");
});
