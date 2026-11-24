"""Settings: la configuración se lee del entorno en un solo lugar y se valida."""
import pytest

from donacion.adapters.ollama_llm_client import OllamaLLMClient
from donacion.config import Settings
from donacion.container import PlatformBuilder


def test_valores_por_defecto():
    s = Settings.from_env({})
    assert s.use_llm is True
    assert (s.ollama_model, s.ollama_host) == ("llama3.2", "http://localhost:11434")
    assert (s.wave_size, s.wave_wait_minutes) == (10, 15.0)
    assert (s.auto_escalate, s.escalation_check_seconds, s.seed_demo) == (True, 30.0, True)
    assert s.token_secret is None


def test_lee_el_entorno():
    s = Settings.from_env({
        "DONACION_USE_LLM": "0", "OLLAMA_MODEL": "qwen2.5:3b", "OLLAMA_HOST": "http://otra:11434/",
        "DONACION_WAVE_SIZE": "3", "DONACION_WAVE_WAIT_MINUTES": "0.25", "DONACION_AUTO_ESCALATE": "0",
        "DONACION_ESCALATION_CHECK_SECONDS": "5", "DONACION_SEED_DEMO": "0", "DONACION_TOKEN_SECRET": "clave",
    })
    assert s.use_llm is False and s.ollama_model == "qwen2.5:3b" and s.ollama_host == "http://otra:11434/"
    assert (s.wave_size, s.wave_wait_minutes) == (3, 0.25)
    assert (s.auto_escalate, s.escalation_check_seconds, s.seed_demo) == (False, 5.0, False)
    assert s.token_secret == b"clave"


@pytest.mark.parametrize("env", [{"DONACION_WAVE_SIZE": "cero"}, {"DONACION_WAVE_SIZE": "0"},
                                 {"DONACION_WAVE_WAIT_MINUTES": "-1"}, {"DONACION_USE_LLM": "talvez"}])
def test_valores_invalidos_se_rechazan_al_arrancar(env):
    with pytest.raises(ValueError):
        Settings.from_env(env)


def test_el_constructor_usa_ollama_con_el_modelo_configurado():
    builder = PlatformBuilder(Settings.from_env({"OLLAMA_MODEL": "qwen2.5:3b", "DONACION_DB": ":memory:"}))
    client = builder.llm_client()
    assert isinstance(client, OllamaLLMClient) and client.model == "qwen2.5:3b"
    assert client.url == "http://localhost:11434/api/chat"
    platform = builder.build()
    assert platform.ai_enabled and platform.ai_provider == "ollama"


def test_sin_ia_no_crea_cliente():
    platform = PlatformBuilder(Settings.from_env({"DONACION_USE_LLM": "0", "DONACION_DB": ":memory:"})).build()
    assert platform.ai_enabled is False and platform.ai_provider is None
