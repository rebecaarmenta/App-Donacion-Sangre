// Sesión del donante: guarda el token firmado que entrega /auth/login (no el id del donante).
// El servidor saca el id del token, así que cambiar lo guardado aquí no permite actuar como otra persona.

const KEY = "donacion.token";

export function createSession(storage) {
  return {
    get: () => storage.getItem(KEY),
    set: token => storage.setItem(KEY, token),
    clear: () => storage.removeItem(KEY),
  };
}

// 401: el token venció o no es válido (p. ej. el servidor se reinició con otra clave).
// 404: los datos viven en memoria y el donante ya no existe.
export function sessionAfterError(status) {
  return status === 401 || status === 404 ? "clear" : "keep";
}
