// Funciones puras de texto para la interfaz (sin DOM, probadas con node --test).

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, ch => HTML_ESCAPES[ch]);
}

// FastAPI responde {detail: "texto"} en errores de dominio y {detail: [{loc, msg}]} en validación (422).
export function errorMessage(detail, status) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map(e => `${(e.loc ?? []).at(-1) ?? "campo"}: ${e.msg}`).join(". ");
  }
  return status >= 500 ? `Error del servidor (${status})` : `Error (${status})`;
}

const URGENCIES = { critica: "crítica", alta: "alta", normal: "normal" };
export function urgencyLabel(value) {
  return URGENCIES[value] ?? value;
}

const STATUSES = {
  apto: "Apto", diferido: "Diferido", no_apto: "No apto", pendiente: "Pendiente",
  abierta: "Abierta", cubierta: "Cubierta", vencida: "Vencida",
};
export function statusLabel(value) {
  return STATUSES[value] ?? value;
}

export function eligibilityText({ status, reasons, eligible_from }) {
  let text = `${statusLabel(status)}: ${reasons.join("; ")}.`;
  if (eligible_from) text += ` Podrás donar desde el ${eligible_from}.`;
  return text;
}

export function describeDispatch(alerts) {
  if (!alerts.length) return "Ya no quedan donantes compatibles por avisar.";
  const n = alerts.length;
  return `Oleada ${alerts[0].wave} enviada a ${n} ${n === 1 ? "donante" : "donantes"}.`;
}
