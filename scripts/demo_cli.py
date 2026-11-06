"""Demo en consola del flujo completo del MVP (útil para grabar el video).

    python scripts/demo_cli.py            # usa IA si hay ANTHROPIC_API_KEY
    DONACION_USE_LLM=0 python scripts/demo_cli.py   # solo reglas
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from donacion.adapters.system_clock import ManualClock  # noqa: E402
from donacion.container import build_platform  # noqa: E402
from donacion.demo import seed_demo  # noqa: E402
from donacion.domain.eligibility import ScreeningAnswers  # noqa: E402
from donacion.services.donor_service import RegisterDonorCommand  # noqa: E402


def title(text: str) -> None:
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def main() -> None:
    clock = ManualClock(datetime.now().replace(second=0, microsecond=0))
    p = build_platform(clock=clock)
    seed_demo(p)
    print(f"Agente con IA (Claude): {'sí' if p.ai_enabled else 'no, solo reglas'}")

    title("1. Registro de un donante nuevo")
    donor = p.register_donor(RegisterDonorCommand(
        name="Mariana Torres", email="mariana@correo.com", password="segura123",
        birth_date=datetime(2002, 4, 10).date(), weight_kg=60, blood_type="A+", lat=20.688, lon=-103.351))
    print(f"{donor.name} ({donor.blood_type}) registrada. Estado: {donor.eligibility.status.value}")

    title("2. Cuestionario de tamizaje")
    result = p.submit_screening(donor.id, ScreeningAnswers())
    print(f"Resultado: {result.status.value} - {', '.join(result.reasons)}")
    for d in p.list_donors():
        e = d.eligibility
        extra = f" (desde {e.eligible_from})" if e.eligible_from else ""
        print(f"  {d.name:<16} {str(d.blood_type):<4} {e.status.value:<9}{extra}  {'; '.join(e.reasons)}")

    title("3. Solicitud urgente: 2 unidades A+ en el Hospital Civil")
    req = p.create_request_valid_for(
        12, requester_name="Familia Pérez", blood_type="A+", units_needed=2,
        hospital_name="Hospital Civil Fray Antonio Alcalde", hospital_lat=20.6866, hospital_lon=-103.3496,
        urgency="critica")
    print(f"Solicitud {req.id} creada ({req.urgency.value}).")

    title("4. El agente filtra y ordena a los candidatos")
    for i, cand in enumerate(p.preview_candidates(req.id), start=1):
        print(f"{i:>2}. {cand.donor.name:<16} {str(cand.donor.blood_type):<4} puntaje {cand.score:>5}  "
              f"{cand.distance_km:>5} km")

    title("5. Primera oleada de alertas")
    alerts = p.dispatch_wave(req.id)
    for a in alerts:
        print(f"-> {a.donor_name}: {a.message}")

    title("6. Dos donantes confirman")
    for a in alerts[:2]:
        req = p.confirm_donation(req.id, a.donor_id)
        print(f"{a.donor_name} confirmó. Unidades: {req.units_confirmed}/{req.units_needed}")
    print(f"Estado final de la solicitud: {req.status.value}")


if __name__ == "__main__":
    main()
