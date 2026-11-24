"""Adaptador de Ollama: el único modelo de IA de la app (local, sin consumo de tokens de pago)."""
import json
import urllib.error

import pytest

from donacion import container
from donacion.adapters.ollama_llm_client import OllamaLLMClient
from donacion.ports.llm import LLMUnavailableError

SCHEMA = {"type": "object", "properties": {"order": {"type": "array"}}, "required": ["order"]}


class FakePost:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def __call__(self, url, payload):
        self.calls.append((url, payload))
        if self.error:
            raise self.error
        return self.reply


def ok(content: str, done_reason="stop"):
    return {"message": {"role": "assistant", "content": content}, "done": True, "done_reason": done_reason}


def test_manda_el_schema_y_devuelve_el_json():
    post = FakePost(ok('{"order": ["d1", "d2"]}'))
    client = OllamaLLMClient(model="llama3.2", host="http://localhost:11434", post=post)
    assert client.complete_json("sistema", "prompt", SCHEMA) == {"order": ["d1", "d2"]}
    url, payload = post.calls[0]
    assert url == "http://localhost:11434/api/chat"
    assert payload["model"] == "llama3.2" and payload["stream"] is False
    assert payload["format"] == SCHEMA
    assert payload["messages"] == [{"role": "system", "content": "sistema"}, {"role": "user", "content": "prompt"}]


@pytest.mark.parametrize("post", [
    FakePost(error=urllib.error.URLError("connection refused")),   # Ollama apagado
    FakePost(error=TimeoutError()),
    FakePost(ok("esto no es json")),
    FakePost(ok("[1, 2]")),
    FakePost(ok('{"order": []', done_reason="length")),               # respuesta cortada
    FakePost({"error": "model 'x' not found"}),
])
def test_cualquier_falla_es_llm_unavailable(post):
    with pytest.raises(LLMUnavailableError):
        OllamaLLMClient(post=post).complete_json("s", "p", SCHEMA)


def test_solo_existe_el_adaptador_de_ollama():
    import pathlib

    import donacion.adapters as adapters
    files = {f.name for f in pathlib.Path(adapters.__file__).parent.glob("*.py")}
    assert "ollama_llm_client.py" in files
    assert not any("claude" in name or "anthropic" in name for name in files)


def test_health_dice_el_proveedor():
    from fastapi.testclient import TestClient

    from donacion.main import create_app
    health = TestClient(create_app(container.build_platform(use_llm=True))).get("/health").json()
    assert health == {"status": "ok", "agente_con_ia": True, "proveedor_ia": "ollama"}
    off = TestClient(create_app(container.build_platform(use_llm=False))).get("/health").json()
    assert off["proveedor_ia"] is None
