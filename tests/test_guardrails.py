from guardrails.guardrails import GUARDRAILS_ENTRADA, entrada_bloqueada
from guardrails.prompts import SALIDA_PROMPT


def test_cinco_guardrails_de_entrada():
    assert set(GUARDRAILS_ENTRADA) == {
        "ofensivo",
        "prompt_injection",
        "off_topic",
        "deshonestidad",
        "pii",
    }


def test_entrada_bloqueada_cualquiera():
    assert entrada_bloqueada({"ofensivo": False, "pii": True}) is True
    assert entrada_bloqueada({"ofensivo": False, "pii": False}) is False


def test_prompts_tienen_marcador():
    assert "{texto}" in SALIDA_PROMPT
    assert all("{texto}" in prompt for prompt in GUARDRAILS_ENTRADA.values())
