// Convierte los datos de los formularios en el JSON que espera la API (sin DOM).
// Los campos vacíos se omiten: un <input type="date"> vacío vale "" y la API respondería 422.

function withoutEmpty(obj) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== "" && v !== undefined));
}

export function buildDonorPayload(form, zone) {
  return withoutEmpty({
    name: form.name,
    email: form.email,
    password: form.password,
    birth_date: form.birth_date,
    weight_kg: form.weight_kg === "" ? "" : Number(form.weight_kg),
    blood_type: form.blood_type,
    lat: zone.lat,
    lon: zone.lon,
    last_donation: form.last_donation,
  });
}

// Edición del perfil: la zona vacía ("Sin cambiar") no toca la ubicación guardada.
export function buildProfilePayload(form, zone) {
  return withoutEmpty({
    name: form.name,
    weight_kg: form.weight_kg === "" ? "" : Number(form.weight_kg),
    lat: zone?.lat,
    lon: zone?.lon,
    last_donation: form.last_donation,
  });
}

export function buildScreeningPayload(form) {
  return withoutEmpty({
    tattoo_or_piercing_date: form.tattoo_or_piercing_date,
    surgery_date: form.surgery_date,
    medication_end_date: form.medication_end_date,
    permanent_exclusion: Boolean(form.permanent_exclusion),
  });
}

// El hospital viaja solo como id del catálogo del servidor: su nombre nunca es texto libre.
export function buildRequestPayload(form) {
  return withoutEmpty({
    requester_name: form.requester_name,
    blood_type: form.blood_type,
    units_needed: Number(form.units_needed),
    urgency: form.urgency,
    hours_valid: Number(form.hours_valid),
    hospital_id: form.hospital,
  });
}
