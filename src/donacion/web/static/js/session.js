// Sesión del donante para el MVP: solo guarda su id en el almacenamiento del navegador (sin tokens).

const KEY = "donacion.donorId";

export function createSession(storage) {
  return {
    get: () => storage.getItem(KEY),
    set: donorId => storage.setItem(KEY, donorId),
    clear: () => storage.removeItem(KEY),
  };
}

// Los datos del servidor viven en memoria: tras reiniciarlo, el donante guardado ya no existe (404).
export function sessionAfterError(status) {
  return status === 404 ? "clear" : "keep";
}
