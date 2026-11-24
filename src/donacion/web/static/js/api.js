// Cliente HTTP de la API. fetch y el lector del token se inyectan para poder probarlo sin servidor.
import { errorMessage } from "./format.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createApi(fetchImpl = (...args) => globalThis.fetch(...args), getToken = () => null) {
  async function request(method, path, body, headers = {}) {
    const init = { method, headers: { ...headers } };
    const token = getToken();
    if (token) init.headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await fetchImpl(path, init);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(errorMessage(data.detail, response.status), response.status);
    }
    return response.json();
  }

  return {
    health: () => request("GET", "/health"),
    registerDonor: payload => request("POST", "/donors", payload),
    login: (email, password) => request("POST", "/auth/login", { email, password }),
    // Rutas del donante: el servidor lo identifica por el token, no por un id en la URL.
    getMe: () => request("GET", "/me"),
    updateProfile: payload => request("PATCH", "/me", payload),
    submitScreening: payload => request("POST", "/me/screening", payload),
    getAlerts: () => request("GET", "/me/alerts"),
    getDonations: () => request("GET", "/me/donations"),
    listHospitals: () => request("GET", "/hospitals"),
    createRequest: payload => request("POST", "/requests", payload),
    getRequest: id => request("GET", `/requests/${encodeURIComponent(id)}`),
    // Manejar una solicitud pide el token que el servidor entregó al crearla.
    getRequestAlerts: (id, token) =>
      request("GET", `/requests/${encodeURIComponent(id)}/alerts`, undefined, { "X-Request-Token": token }),
    getCandidates: (id, token) =>
      request("GET", `/requests/${encodeURIComponent(id)}/candidates`, undefined, { "X-Request-Token": token }),
    dispatch: (id, token) =>
      request("POST", `/requests/${encodeURIComponent(id)}/dispatch`, undefined, { "X-Request-Token": token }),
    confirm: requestId => request("POST", `/requests/${encodeURIComponent(requestId)}/confirm`),
    escalate: () => request("POST", "/requests/escalate"),
  };
}
