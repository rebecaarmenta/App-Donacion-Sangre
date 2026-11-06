// Zonas y hospitales de la zona metropolitana de Guadalajara (evita pedir coordenadas al usuario).

export const ZONES = [
  { id: "centro", name: "Centro Guadalajara", lat: 20.6767, lon: -103.3475 },
  { id: "chapultepec", name: "Chapultepec", lat: 20.6720, lon: -103.3700 },
  { id: "zapopan", name: "Zapopan Centro", lat: 20.7214, lon: -103.3918 },
  { id: "tlaquepaque", name: "Tlaquepaque", lat: 20.6400, lon: -103.3100 },
  { id: "tonala", name: "Tonalá", lat: 20.6240, lon: -103.2340 },
  { id: "tlajomulco", name: "Tlajomulco", lat: 20.4736, lon: -103.4440 },
];

export const HOSPITALS = [
  { id: "hc-fray-antonio", name: "Hospital Civil Fray Antonio Alcalde", lat: 20.6866, lon: -103.3496 },
  { id: "hc-juan-menchaca", name: "Hospital Civil Juan I. Menchaca", lat: 20.6981, lon: -103.3324 },
  { id: "cmno", name: "Centro Médico Nacional de Occidente", lat: 20.6835, lon: -103.3266 },
  { id: "cets", name: "Centro Estatal de la Transfusión Sanguínea", lat: 20.6731, lon: -103.3600 },
];

export const BLOOD_TYPES = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];
