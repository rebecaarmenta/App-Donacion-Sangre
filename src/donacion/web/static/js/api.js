// Cliente HTTP de la API. fetch se inyecta para poder probarlo sin servidor.
import { errorMessage } from "./format.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createApi(fetchImpl = (...args) => globalThis.fetch(...args)) {
  async function request(method, path, body) {
    const init = { method, headers: {} };
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
    getDonor: id => request("GET", `/donors/${encodeURIComponent(id)}`),
    submitScreening: (id, payload) => request("POST", `/donors/${encodeURIComponent(id)}/screening`, payload),
    getAlerts: id => request("GET", `/donors/${encodeURIComponent(id)}/alerts`),
    createRequest: payload => request("POST", "/requests", payload),
    getRequest: id => request("GET", `/requests/${encodeURIComponent(id)}`),
    getCandidates: id => request("GET", `/requests/${encodeURIComponent(id)}/candidates`),
    dispatch: id => request("POST", `/requests/${encodeURIComponent(id)}/dispatch`),
    confirm: (requestId, donorId) =>
      request("POST", `/requests/${encodeURIComponent(requestId)}/confirm`, { donor_id: donorId }),
    escalate: () => request("POST", "/requests/escalate"),
  };
}
