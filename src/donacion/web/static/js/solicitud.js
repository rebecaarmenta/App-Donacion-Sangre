// Página de la solicitud: el familiar crea la solicitud y coordina las oleadas del agente.
import { createApi } from "./api.js";
import { BLOOD_TYPES } from "./catalogs.js";
import { describeCreated, describeDispatch, escapeHtml, statusLabel, urgencyLabel } from "./format.js";
import { whileDisabled } from "./busy.js";
import { buildRequestPayload } from "./payloads.js";

const api = createApi();
const KEY = "donacion.requestId";
const TOKEN_KEY = "donacion.requestToken";  // lo entrega el servidor al crear; sin él no se maneja la solicitud
const $ = id => document.getElementById(id);
const REFRESH_MS = 10000;  // el escalamiento ocurre en el servidor: la página se actualiza sola
// Mientras el agente arma una oleada (con IA puede tardar ~1 min) el botón no se reactiva,
// ni siquiera cuando la página se actualiza sola: así un segundo clic no manda otra oleada.
let dispatching = false;

function showMessage(text, kind = "ok") {
  const box = $("mensaje");
  box.textContent = text;
  box.className = `mensaje ${kind}`;
}

function fillSelect(select, options) {
  select.innerHTML = options
    .map(o => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`)
    .join("");
}

function currentId() {
  return localStorage.getItem(KEY);
}

function currentToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function forgetRequest() {
  localStorage.removeItem(KEY);
  localStorage.removeItem(TOKEN_KEY);
}

function renderStatus(request) {
  $("estado-resumen").innerHTML = `
    <span class="insignia insignia-${escapeHtml(request.status)}">${escapeHtml(statusLabel(request.status))}</span>
    <span>Sangre <strong>${escapeHtml(request.blood_type)}</strong></span>
    <span><strong>${request.units_confirmed}/${request.units_needed}</strong> unidades confirmadas</span>
    <span>Urgencia ${escapeHtml(urgencyLabel(request.urgency))}</span>
    <span>${escapeHtml(request.hospital)}</span>
    <span>Oleadas enviadas: ${request.waves_sent}</span>`;
  const open = request.status === "abierta";
  $("btn-oleada").disabled = !open || dispatching;
  $("btn-candidatos").disabled = !open;
  $("form-solicitud").classList.add("oculto");
  $("seccion-estado").classList.remove("oculto");
}

function renderCandidates(candidates) {
  const body = $("tabla-candidatos").querySelector("tbody");
  if (!candidates.length) {
    body.innerHTML = '<tr><td colspan="6" class="ayuda">No hay donantes compatibles, aptos y cercanos.</td></tr>';
    return;
  }
  body.innerHTML = candidates.map(c => `
    <tr>
      <td>${c.position}</td>
      <td>${escapeHtml(c.name)}</td>
      <td>${escapeHtml(c.blood_type)}</td>
      <td>${c.score}</td>
      <td>${c.distance_km} km</td>
      <td><ul>${c.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul></td>
    </tr>`).join("");
}

function renderAlerts(alerts) {
  const list = $("lista-oleadas");
  if (!alerts.length) {
    list.innerHTML = '<li class="meta">Aún no se ha enviado ninguna oleada.</li>';
    return;
  }
  const waves = [...new Set(alerts.map(a => a.wave))].sort((a, b) => b - a);
  list.innerHTML = waves.map(w => `
    <li>
      <h3>Oleada ${w}</h3>
      ${alerts.filter(a => a.wave === w)
        .map(a => `<p><strong>${escapeHtml(a.donor_name)}</strong>: ${escapeHtml(a.message)}</p>`).join("")}
    </li>`).join("");
}

async function refresh() {
  const id = currentId();
  if (!id) return;
  try {
    const [request, alerts] = await Promise.all([api.getRequest(id), api.getRequestAlerts(id, currentToken())]);
    renderStatus(request);
    renderAlerts(alerts);
  } catch (error) {
    if ([401, 403, 404].includes(error.status)) {
      forgetRequest();
      showMessage("La solicitud guardada ya no está disponible (el servidor se reinició o venció su acceso). Crea una nueva.", "error");
      $("form-solicitud").classList.remove("oculto");
      $("seccion-estado").classList.add("oculto");
      return;
    }
    showMessage(error.message, "error");
  }
}

async function run(action) {
  try {
    await action();
  } catch (error) {
    showMessage(error.message, "error");
  }
  await refresh();
}

// ---------- eventos ----------
$("form-solicitud").addEventListener("submit", event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target).entries());
  const button = event.target.querySelector('button[type="submit"]');
  whileDisabled(button, () => run(async () => {
    const request = await api.createRequest(buildRequestPayload(data));
    localStorage.setItem(KEY, request.id);
    localStorage.setItem(TOKEN_KEY, request.manage_token);
    showMessage(describeCreated(request), request.notified_donors.length ? "ok" : "error");
  }));
});

$("btn-candidatos").addEventListener("click", () => run(async () => {
  const candidates = await api.getCandidates(currentId(), currentToken());
  renderCandidates(candidates);
  showMessage(`El agente encontró ${candidates.length} candidatos compatibles, aptos y cercanos.`);
}));

$("btn-oleada").addEventListener("click", async () => {
  if (dispatching) return;
  dispatching = true;
  $("btn-oleada").disabled = true;
  showMessage("El agente está eligiendo a los siguientes donantes…");
  try {
    await run(async () => {
      const alerts = await api.dispatch(currentId(), currentToken());
      showMessage(describeDispatch(alerts), alerts.length ? "ok" : "error");
    });
  } finally {
    dispatching = false;
    await refresh();   // deja el botón según el estado real (desactivado si ya se cubrió)
  }
});

$("btn-refrescar").addEventListener("click", () => run(async () => {}));

$("btn-nueva").addEventListener("click", () => {
  forgetRequest();
  renderAlerts([]);
  $("mensaje").className = "mensaje oculto";
  $("form-solicitud").classList.remove("oculto");
  $("seccion-estado").classList.add("oculto");
});

// ---------- inicio ----------
fillSelect(document.querySelector('#form-solicitud select[name="blood_type"]'),
  BLOOD_TYPES.map(t => ({ value: t, label: t })));
api.listHospitals()
  .then(hospitals => fillSelect(document.querySelector('#form-solicitud select[name="hospital"]'),
    hospitals.map(h => ({ value: h.id, label: h.name }))))
  .catch(error => showMessage(error.message, "error"));
fillSelect(document.querySelector('#form-solicitud select[name="urgency"]'),
  ["critica", "alta", "normal"].map(u => ({ value: u, label: urgencyLabel(u) })));

refresh();
setInterval(() => { if (currentId() && !document.hidden) refresh(); }, REFRESH_MS);
