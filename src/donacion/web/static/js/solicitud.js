// Página de la solicitud: el familiar crea la solicitud y coordina las oleadas del agente.
import { createApi } from "./api.js";
import { BLOOD_TYPES, HOSPITALS } from "./catalogs.js";
import { describeDispatch, escapeHtml, statusLabel, urgencyLabel } from "./format.js";
import { buildRequestPayload } from "./payloads.js";

const api = createApi();
const KEY = "donacion.requestId";
const $ = id => document.getElementById(id);
const sentAlerts = [];  // alertas enviadas en esta sesión del navegador, para mostrarlas por oleada

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

function renderStatus(request) {
  $("estado-resumen").innerHTML = `
    <span class="insignia insignia-${escapeHtml(request.status)}">${escapeHtml(statusLabel(request.status))}</span>
    <span>Sangre <strong>${escapeHtml(request.blood_type)}</strong></span>
    <span><strong>${request.units_confirmed}/${request.units_needed}</strong> unidades confirmadas</span>
    <span>Urgencia ${escapeHtml(urgencyLabel(request.urgency))}</span>
    <span>${escapeHtml(request.hospital)}</span>
    <span>Oleadas enviadas: ${request.waves_sent}</span>`;
  const open = request.status === "abierta";
  for (const id of ["btn-oleada", "btn-escalar", "btn-candidatos"]) $(id).disabled = !open;
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

function renderAlerts() {
  const list = $("lista-oleadas");
  if (!sentAlerts.length) {
    list.innerHTML = '<li class="meta">Aún no se ha enviado ninguna oleada.</li>';
    return;
  }
  const waves = [...new Set(sentAlerts.map(a => a.wave))].sort((a, b) => b - a);
  list.innerHTML = waves.map(w => `
    <li>
      <h3>Oleada ${w}</h3>
      ${sentAlerts.filter(a => a.wave === w)
        .map(a => `<p><strong>${escapeHtml(a.donor_name)}</strong>: ${escapeHtml(a.message)}</p>`).join("")}
    </li>`).join("");
}

async function refresh() {
  const id = currentId();
  if (!id) return;
  try {
    renderStatus(await api.getRequest(id));
  } catch (error) {
    if (error.status === 404) {
      localStorage.removeItem(KEY);
      showMessage("La solicitud guardada ya no existe (el servidor se reinició). Crea una nueva.", "error");
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
  const hospital = HOSPITALS.find(h => h.id === data.hospital);
  run(async () => {
    const request = await api.createRequest(buildRequestPayload(data, hospital));
    localStorage.setItem(KEY, request.id);
    sentAlerts.length = 0;
    renderAlerts();
    showMessage(`Solicitud creada. Ahora revisa a los candidatos o envía la primera oleada.`);
  });
});

$("btn-candidatos").addEventListener("click", () => run(async () => {
  const candidates = await api.getCandidates(currentId());
  renderCandidates(candidates);
  showMessage(`El agente encontró ${candidates.length} candidatos compatibles, aptos y cercanos.`);
}));

$("btn-oleada").addEventListener("click", () => run(async () => {
  const alerts = await api.dispatch(currentId());
  sentAlerts.push(...alerts);
  renderAlerts();
  showMessage(describeDispatch(alerts), alerts.length ? "ok" : "error");
}));

$("btn-escalar").addEventListener("click", () => run(async () => {
  const result = await api.escalate();
  const alerts = result[currentId()] ?? [];
  if (!alerts.length) {
    showMessage("Aún no toca otra oleada (espera de 15 minutos).");
    return;
  }
  sentAlerts.push(...alerts);
  renderAlerts();
  showMessage(describeDispatch(alerts));
}));

$("btn-refrescar").addEventListener("click", () => run(async () => {}));

$("btn-nueva").addEventListener("click", () => {
  localStorage.removeItem(KEY);
  sentAlerts.length = 0;
  renderAlerts();
  $("mensaje").className = "mensaje oculto";
  $("form-solicitud").classList.remove("oculto");
  $("seccion-estado").classList.add("oculto");
});

// ---------- inicio ----------
fillSelect(document.querySelector('#form-solicitud select[name="blood_type"]'),
  BLOOD_TYPES.map(t => ({ value: t, label: t })));
fillSelect(document.querySelector('#form-solicitud select[name="hospital"]'),
  HOSPITALS.map(h => ({ value: h.id, label: h.name })));
fillSelect(document.querySelector('#form-solicitud select[name="urgency"]'),
  ["critica", "alta", "normal"].map(u => ({ value: u, label: urgencyLabel(u) })));

api.health()
  .then(h => { $("indicador-ia").textContent = h.agente_con_ia ? "Agente con IA (Claude)" : "Agente con reglas"; })
  .catch(() => { $("indicador-ia").textContent = "Sin conexión con el servidor"; });
refresh();
