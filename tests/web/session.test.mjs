import test from "node:test";
import assert from "node:assert/strict";
import { createSession, sessionAfterError } from "../../src/donacion/web/static/js/session.js";

const memoryStorage = () => { const m = new Map();
  return { getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, v), removeItem: k => m.delete(k) }; };

test("guarda, lee y borra", () => {
  const s = createSession(memoryStorage());
  assert.equal(s.get(), null); s.set("abc"); assert.equal(s.get(), "abc"); s.clear(); assert.equal(s.get(), null);
});
test("404 cierra la sesión", () => {
  assert.equal(sessionAfterError(404), "clear");
  assert.equal(sessionAfterError(409), "keep");
});
