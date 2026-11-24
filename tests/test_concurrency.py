"""Lo que pasa MIENTRAS la IA piensa (alrededor de un minuto con Ollama local) no se pierde.

Con SQLite cada parte del código trabaja con su propia copia de la solicitud. Si una oleada
guarda la copia que leyó antes de consultar a la IA, borra lo que ocurrió mientras tanto:
una confirmación, o una oleada que se adelantó (y entonces la vuelve a mandar repetida).
"""
from dataclasses import replace

from donacion.config import Settings
from donacion.container import build_platform
from donacion.demo import seed_demo
from donacion.domain.blood_request import RequestStatus
from donacion.ports.llm import LLMClient, LLMUnavailableError


class SlowLLM(LLMClient):
    """La primera vez que se le consulta ejecuta `while_thinking` (lo que hace otra persona mientras
    tanto) y luego falla, así el agente sigue con sus reglas."""

    def __init__(self) -> None:
        self.while_thinking = None

    def complete_json(self, system, prompt, schema):
        action, self.while_thinking = self.while_thinking, None
        if action:
            action()
        raise LLMUnavailableError("respuesta lenta simulada")


def make_platform(clock):
    llm = SlowLLM()
    settings = replace(Settings.from_env(), database_path=":memory:", use_llm=True, wave_size=3)
    p = build_platform(settings=settings, clock=clock, llm_client=llm)
    seed_demo(p)
    return p, llm


def new_request(p):
    return p.create_request_valid_for(12, requester_name="F", blood_type="A+", units_needed=1,
                                      hospital_id="hc-fray-antonio", urgency="critica")


def test_una_confirmacion_mientras_la_ia_piensa_no_se_pierde(clock):
    p, llm = make_platform(clock)
    req = new_request(p)
    donor = req.notified_donors[0]
    llm.while_thinking = lambda: p.confirm_donation(req.id, donor)

    assert p.dispatch_wave(req.id) == []           # se cubrió mientras pensaba: ya no avisa a nadie más

    saved = p.get_request(req.id)
    assert saved.status is RequestStatus.COVERED and saved.confirmed_donors == (donor,)
    assert saved.waves_sent == 1


def test_el_escalamiento_no_borra_lo_que_paso_en_otra_solicitud(clock):
    p, llm = make_platform(clock)
    first, second = new_request(p), new_request(p)
    donor = second.notified_donors[0]
    clock.advance(15)
    # mientras la IA piensa la oleada 2 de la primera, alguien confirma en la segunda
    llm.while_thinking = lambda: p.confirm_donation(second.id, donor)

    sent = p.escalate()

    saved = p.get_request(second.id)
    assert saved.status is RequestStatus.COVERED and saved.confirmed_donors == (donor,)
    assert second.id not in sent and saved.waves_sent == 1


def test_adelantar_una_oleada_mientras_se_escala_no_la_repite(clock):
    p, llm = make_platform(clock)
    first, second = new_request(p), new_request(p)
    clock.advance(15)
    # mientras la IA piensa la oleada 2 de la primera, la familia de la segunda la adelanta
    llm.while_thinking = lambda: p.dispatch_wave(second.id)

    p.escalate()

    alerts = p.alerts_for_request(second.id)
    donors = [a.donor_id for a in alerts]
    assert len(donors) == len(set(donors))          # nadie recibe la misma alerta dos veces
    assert sorted({a.wave for a in alerts}) == [1, 2]
    assert p.get_request(second.id).waves_sent == 2
