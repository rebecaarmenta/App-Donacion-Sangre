import test from "node:test";
import assert from "node:assert/strict";
import { whileDisabled } from "../../src/donacion/web/static/js/busy.js";

test("el botón queda desactivado mientras trabaja y se reactiva al terminar", async () => {
  const button = { disabled: false };
  let during;
  await whileDisabled(button, async () => { during = button.disabled; });
  assert.equal(during, true);
  assert.equal(button.disabled, false);
});

test("un segundo clic mientras trabaja no repite la acción", async () => {
  const button = { disabled: false };
  let calls = 0, release;
  const first = whileDisabled(button, () => { calls++; return new Promise(r => { release = r; }); });
  await whileDisabled(button, async () => { calls++; });   // doble clic
  release();
  await first;
  assert.equal(calls, 1);
});

test("si la acción falla, el botón se reactiva y el error sigue", async () => {
  const button = { disabled: false };
  await assert.rejects(whileDisabled(button, async () => { throw new Error("x"); }), /x/);
  assert.equal(button.disabled, false);
});
