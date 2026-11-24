// Zonas de la zona metropolitana de Guadalajara (evita pedir coordenadas al usuario).
// Los hospitales los da el servidor (GET /hospitals) para que solo existan en un catálogo.

export const ZONES = [
  { id: "centro", name: "Centro Guadalajara", lat: 20.6767, lon: -103.3475 },
  { id: "chapultepec", name: "Chapultepec", lat: 20.6720, lon: -103.3700 },
  { id: "zapopan", name: "Zapopan Centro", lat: 20.7214, lon: -103.3918 },
  { id: "tlaquepaque", name: "Tlaquepaque", lat: 20.6400, lon: -103.3100 },
  { id: "tonala", name: "Tonalá", lat: 20.6240, lon: -103.2340 },
  { id: "tlajomulco", name: "Tlajomulco", lat: 20.4736, lon: -103.4440 },
];

export const BLOOD_TYPES = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];
