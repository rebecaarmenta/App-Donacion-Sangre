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

// Mensaje al guardar el perfil. Solo pide repetir el cuestionario si ESTE cambio invalidó un
// resultado que ya tenía (apto, diferido o no apto pasa a pendiente). Una cuenta nueva ya está
// pendiente y cambiar su nombre o su zona no debe decir "cambiaste tu peso".
export function describeProfileSaved(before, after) {
  const wasScreened = before && before.eligibility.status !== "pendiente";
  if (wasScreened && after.eligibility.status === "pendiente") {
    return { text: "Guardamos tus cambios. Como cambiaste tu peso o tu última donación, contesta de nuevo el cuestionario.",
      kind: "error" };
  }
  return { text: "Guardamos tus cambios.", kind: "ok" };
}

// Resumen del impacto del donante (historial de donaciones).
export function describeImpact(history) {
  const { total, requests_covered: covered } = history;
  if (!total) return "Aún no tienes donaciones registradas en la app.";
  const veces = `Has donado ${total} ${total === 1 ? "vez" : "veces"}`;
  if (!covered) return `${veces}.`;
  return `${veces} y ayudaste a cubrir ${covered} ${covered === 1 ? "solicitud" : "solicitudes"}.`;
}

// Mensaje al crear la solicitud: la primera oleada ya salió.
export function describeCreated(request) {
  const n = request.notified_donors.length;
  if (!n) return "Solicitud creada, pero no hay donantes compatibles, aptos y cercanos por avisar.";
  return `Solicitud creada. El agente ya avisó a ${n} ${n === 1 ? "donante" : "donantes"} (oleada 1).`;
}
