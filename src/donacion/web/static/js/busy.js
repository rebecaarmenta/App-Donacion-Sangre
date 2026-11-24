// Evita que un doble clic repita una acción (p. ej. crear dos solicitudes iguales):
// el botón queda desactivado mientras la acción trabaja y se reactiva al terminar, aunque falle.

export async function whileDisabled(button, action) {
  if (button.disabled) return;   // ya hay una acción en curso con este botón
  button.disabled = true;
  try {
    return await action();
  } finally {
    button.disabled = false;
  }
}
