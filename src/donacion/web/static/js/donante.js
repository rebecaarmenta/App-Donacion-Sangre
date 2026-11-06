// Página del donante: conecta donante.html con la API. La lógica probable vive en los otros módulos.
import { ApiError, createApi } from "./api.js";
import { BLOOD_TYPES, ZONES } from "./catalogs.js";
import { eligibilityText, escapeHtml, statusLabel, urgencyLabel } from "./format.js";
import { buildDonorPayload, buildScreeningPayload } from "./payloads.js";
import { createSession, sessionAfterError } from "./session.js";

const api = createApi();
const session = createSession(window.localStorage);
const $ = id => document.getElementById(id);

function showMessage(text, kind = "ok") {
  const box = $("mensaje");
  box.textContent = text;
  box.className = `mensaje ${kind}`;
}

function clearMessage() {
  $("mensaje").className = "mensaje oculto";
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function fillSelect(select, options) {
  select.innerHTML = options
    .map(o => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`)
    .join("");
}

function handleError(error) {
  if (error instanceof ApiError && session.get() && sessionAfterError(error.status) === "clear") {
    session.clear();
    showLoggedOut();
    showMessage("Tu sesión ya no es válida (el servidor se reinició). Entra o regístrate de nuevo.", "error");
    return;
  }
  showMessage(error.message || "Ocurrió un error inesperado.", "error");
}

function showLoggedOut() {
  $("seccion-acceso").classList.remove("oculto");
  $("seccion-perfil").classList.add("oculto");
}

function renderProfile(donor) {
  $("perfil-nombre").textContent = donor.name;
  $("perfil-tipo").textContent = donor.blood_type;
  const badge = $("perfil-estado");
  badge.textContent = statusLabel(donor.eligibility.status);
  badge.className = `insignia insignia-${donor.eligibility.status}`;
  $("perfil-detalle").textContent = eligibilityText(donor.eligibility);
}

async function renderAlerts(donorId) {
  const list = $("lista-alertas");
  const alerts = await api.getAlerts(donorId);
  if (!alerts.length) {
    list.innerHTML = '<li class="meta">Todavía no tienes alertas. Te avisaremos cuando alguien te necesite.</li>';
    return;
  }
  const requests = await Promise.all(alerts.map(a => api.getRequest(a.request_id)));
  list.innerHTML = alerts.map((alert, i) => {
    const request = requests[i];
    const confirmed = request.confirmed_donors.includes(donorId);
    const canConfirm = request.status === "abierta" && !confirmed;
    const action = confirmed
      ? '<span class="insignia insignia-apto">Confirmaste tu donación</span>'
      : canConfirm
        ? `<button class="btn" data-request="${escapeHtml(alert.request_id)}">Confirmo que voy a donar</button>`
        : `<span class="insignia insignia-${escapeHtml(request.status)}">Solicitud ${escapeHtml(statusLabel(request.status).toLowerCase())}</span>`;
    return `<li>
      <p>${escapeHtml(alert.message)}</p>
      <p class="meta">Oleada ${alert.wave} · ${escapeHtml(request.hospital)} · urgencia ${escapeHtml(urgencyLabel(request.urgency))}
        · ${request.units_confirmed}/${request.units_needed} unidades</p>
      ${action}
    </li>`;
  }).join("");
}

async function loadProfile() {
  const donorId = session.get();
  if (!donorId) return showLoggedOut();
  try {
    renderProfile(await api.getDonor(donorId));
    await renderAlerts(donorId);
    $("seccion-acceso").classList.add("oculto");
    $("seccion-perfil").classList.remove("oculto");
  } catch (error) {
    handleError(error);
  }
}

// ---------- eventos ----------
$("form-registro").addEventListener("submit", async event => {
  event.preventDefault();
  const data = formData(event.target);
  const zone = ZONES.find(z => z.id === data.zone);
  try {
    const donor = await api.registerDonor(buildDonorPayload(data, zone));
    session.set(donor.id);
    event.target.reset();
    showMessage(`¡Bienvenida/o, ${donor.name}! Ahora contesta el cuestionario para saber si puedes donar.`);
    await loadProfile();
  } catch (error) {
    handleError(error);
  }
});

$("form-acceso").addEventListener("submit", async event => {
  event.preventDefault();
  const { email, password } = formData(event.target);
  try {
    const donor = await api.login(email, password);
    session.set(donor.id);
    event.target.reset();
    clearMessage();
    await loadProfile();
  } catch (error) {
    handleError(error);
  }
});

$("form-tamizaje").addEventListener("submit", async event => {
  event.preventDefault();
  const data = formData(event.target);
  data.permanent_exclusion = event.target.elements.permanent_exclusion.checked;
  try {
    const result = await api.submitScreening(session.get(), buildScreeningPayload(data));
    showMessage(eligibilityText(result), result.status === "apto" ? "ok" : "error");
    await loadProfile();
  } catch (error) {
    handleError(error);
  }
});

$("lista-alertas").addEventListener("click", async event => {
  const button = event.target.closest("button[data-request]");
  if (!button) return;
  button.disabled = true;
  try {
    const request = await api.confirm(button.dataset.request, session.get());
    showMessage(`¡Gracias! Tu donación quedó confirmada (${request.units_confirmed}/${request.units_needed} unidades).`);
    await loadProfile();
  } catch (error) {
    button.disabled = false;
    handleError(error);
  }
});

$("btn-actualizar").addEventListener("click", () => loadProfile());

$("btn-salir").addEventListener("click", () => {
  session.clear();
  clearMessage();
  showLoggedOut();
});

// ---------- inicio ----------
fillSelect(document.querySelector('#form-registro select[name="blood_type"]'),
  BLOOD_TYPES.map(t => ({ value: t, label: t })));
fillSelect(document.querySelector('#form-registro select[name="zone"]'),
  ZONES.map(z => ({ value: z.id, label: z.name })));
loadProfile();
