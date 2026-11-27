"""Evaluadores de guardrails basados en LLM."""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from dotenv import load_dotenv

from judges.juez import crear_juez as _crear_juez
from guardrails.prompts import (
    DESHONESTIDAD_PROMPT,
    OFF_TOPIC_PROMPT,
    OFENSIVO_PROMPT,
    PII_PROMPT,
    PROMPT_INJECTION_PROMPT,
    SALIDA_PROMPT,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

GUARDRAILS_ENTRADA = {
    "ofensivo": OFENSIVO_PROMPT,
    "prompt_injection": PROMPT_INJECTION_PROMPT,
    "off_topic": OFF_TOPIC_PROMPT,
    "deshonestidad": DESHONESTIDAD_PROMPT,
    "pii": PII_PROMPT,
}


def crear_juez():
    """Juez de guardrails. Prioriza OpenAI si hay clave configurada."""
    return _crear_juez(max_tokens=10, timeout=30)


def _evaluar(nombre: str, prompt: str, texto: str, juez) -> tuple:
    try:
        respuesta = juez.invoke(prompt.format(texto=texto[:4000])).content.strip().lower()
        return nombre, "true" in respuesta
    except Exception as exc:
        return nombre, False


def validar_entrada(texto: str) -> Dict[str, bool]:
    """Devuelve un dict con el resultado de cada guardrail de entrada."""
    juez = crear_juez()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = [
            executor.submit(_evaluar, nombre, prompt, texto, juez)
            for nombre, prompt in GUARDRAILS_ENTRADA.items()
        ]
        return dict(futuro.result() for futuro in futuros)


def entrada_bloqueada(resultado: Dict[str, bool]) -> bool:
    return any(resultado.values())


def validar_salida(texto: str) -> bool:
    """Devuelve True si la respuesta es adecuada, False si el guardrail la rechaza."""
    juez = crear_juez()
    _, adecuado = _evaluar("salida", SALIDA_PROMPT, texto, juez)
    return adecuado
