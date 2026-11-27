"""Utilidades de medición de latencia, tokens, costo y errores."""

import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator

from observability.logger import registrar_evento


@contextmanager
def medir_latencia() -> Iterator[Dict[str, float]]:
    """Context manager que devuelve la latencia en milisegundos."""
    medicion: Dict[str, float] = {}
    inicio = time.perf_counter()
    try:
        yield medicion
    finally:
        medicion["latencia_ms"] = round((time.perf_counter() - inicio) * 1000, 2)


def summarize_usage(usage: Dict[str, Any]) -> Dict[str, int]:
    """Suma el uso de tokens de todas las llamadas del dict de LangChain."""
    prompt = 0
    completion = 0
    for datos in (usage or {}).values():
        prompt += int(getattr(datos, "input_tokens", 0) or 0)
        completion += int(getattr(datos, "output_tokens", 0) or 0)
    return {
        "prompt": prompt,
        "completion": completion,
        "total": prompt + completion,
    }


def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Costo estimado en USD según precios por millón definidos en .env."""
    precio_entrada = float(os.getenv("PRICE_INPUT_PER_1M", "0"))
    precio_salida = float(os.getenv("PRICE_OUTPUT_PER_1M", "0"))
    return (prompt_tokens * precio_entrada + completion_tokens * precio_salida) / 1_000_000


def request_failed(error: Any, thread_id: str = "sin_thread", etapa: str = "agente") -> None:
    """Registra un evento de fallo para análisis posterior."""
    registrar_evento("error", {
        "thread_id": thread_id,
        "etapa": etapa,
        "error": f"{type(error).__name__}: {error}",
    })
