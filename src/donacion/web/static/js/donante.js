// Página del donante: conecta donante.html con la API. La lógica probable vive en los otros módulos.
import { ApiError, createApi } from "./api.js";
import { BLOOD_TYPES, ZONES } from "./catalogs.js";
import { describeImpact, describeProfileSaved, eligibilityText, escapeHtml, statusLabel, urgencyLabel } from "./format.js";
import { buildDonorPayload, buildProfilePayload, buildScreeningPayload } from "./payloads.js";
import { createSession, sessionAfterError } from "./session.js";

const session = createSession(window.localStorage);
const api = createApi(undefined, session.get);
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
    showMessage("Tu sesión ya no es válida (venció o el servidor se reinició). Entra o regístrate de nuevo.", "error");
    return;
  }
  showMessage(error.message || "Ocurrió un error inesperado.", "error");
}

function showLoggedOut() {
  $("seccion-acceso").classList.remove("oculto");
  $("seccion-perfil").classList.add("oculto");
}

// El perfil se recarga cada 15 s: no se pisa lo que el donante está escribiendo.
let profileFormDirty = false;
let currentDonor = null;  // el perfil tal como se mostró; sirve para comparar antes y después de guardar

function fillProfileForm(donor) {
  if (profileFormDirty) return;
  const form = $("form-perfil").elements;
  form.name.value = donor.name;
  form.weight_kg.value = donor.weight_kg;
  form.zone.value = "";
  form.last_donation.value = donor.last_donation ?? "";
}

function renderProfile(donor) {
  currentDonor = donor;
  fillProfileForm(donor);
  $("perfil-nombre").textContent = donor.name;
  $("perfil-tipo").textContent = donor.blood_type;
  const badge = $("perfil-estado");
  badge.textContent = statusLabel(donor.eligibility.status);
  badge.className = `insignia insignia-${donor.eligibility.status}`;
  $("perfil-detalle").textContent = eligibilityText(donor.eligibility);
}

async function renderAlerts(donorId) {
  const list = $("lista-alertas");
  const alerts = await api.getAlerts();
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

async function renderDonations() {
  const history = await api.getDonations();
  $("historial-resumen").textContent = describeImpact(history);
  $("lista-donaciones").innerHTML = history.donations.map(d => `
    <li><strong>${escapeHtml(d.date)}</strong> · ${escapeHtml(d.hospital ?? "Hospital no registrado")}</li>`).join("");
}

async function loadProfile() {
  if (!session.get()) return showLoggedOut();
  try {
    const donor = await api.getMe();
    renderProfile(donor);
    await Promise.all([renderAlerts(donor.id), renderDonations()]);
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
    session.set((await api.login(data.email, data.password)).access_token);
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
    session.set((await api.login(email, password)).access_token);
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
    const result = await api.submitScreening(buildScreeningPayload(data));
    showMessage(eligibilityText(result), result.status === "apto" ? "ok" : "error");
    await loadProfile();
  } catch (error) {
    handleError(error);
  }
});

$("form-perfil").addEventListener("input", () => { profileFormDirty = true; });

$("form-perfil").addEventListener("submit", async event => {
  event.preventDefault();
  const data = formData(event.target);
  const zone = ZONES.find(z => z.id === data.zone);
  try {
    const before = currentDonor;
    const donor = await api.updateProfile(buildProfilePayload(data, zone));
    profileFormDirty = false;
    const { text, kind } = describeProfileSaved(before, donor);
    showMessage(text, kind);
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
    const request = await api.confirm(button.dataset.request);
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
fillSelect(document.querySelector('#form-perfil select[name="zone"]'),
  [{ value: "", label: "Sin cambiar" }, ...ZONES.map(z => ({ value: z.id, label: z.name }))]);
loadProfile();
// Las oleadas pueden llegar en cualquier momento (escalamiento automático): revisa cada 15 s.
setInterval(() => { if (session.get() && !document.hidden) loadProfile(); }, 15000);
