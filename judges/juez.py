"""Fábrica del juez LLM.

Prioriza OpenAI cuando hay OPENAI_API_KEY. Si no la hay, usa Groq.
El agente bajo evaluación no cambia: este módulo solo crea evaluadores.
"""

import os
from typing import Any

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))


def crear_juez(max_tokens: int = 180, timeout: int = 60) -> Any:
    """Devuelve un ChatOpenAI o ChatGroq con temperatura 0."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key.startswith("sk-") and len(openai_key) > 20:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=max_tokens,
            api_key=openai_key,
            max_retries=2,
            timeout=timeout,
        )

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key.startswith("gsk_") and len(groq_key) > 15:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="qwen/qwen3.8-27b",
            temperature=0.0,
            max_tokens=max_tokens,
            api_key=groq_key,
            max_retries=2,
            timeout=timeout,
        )

    raise RuntimeError("Se requiere OPENAI_API_KEY o GROQ_API_KEY para el juez LLM.")


def proveedor_activo() -> str:
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key.startswith("sk-") and len(openai_key) > 20:
        return "openai:gpt-4o-mini"
    return "groq:qwen/qwen3.8-27b"
