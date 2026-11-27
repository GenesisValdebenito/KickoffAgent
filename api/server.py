"""API FastAPI para KickoffAgent.

Endpoints:
    GET  /health
    POST /ask
    GET  /metrics
    GET  /logs
    POST /eval

Ejecución:
    uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
"""

import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.kickoff_agent import (  # noqa: E402
    DOCUMENTOS_REGISTRADOS,
    agent_executor,
    invocar_agente_seguro,
)
from observability.logger import leer_logs  # noqa: E402
from observability.metrics import summarize_usage  # noqa: E402
from guardrails.guardrails import (  # noqa: E402
    entrada_bloqueada,
    validar_entrada,
    validar_salida,
)

app = FastAPI(
    title="KickoffAgent API",
    description="API de consulta, métricas y evaluación de KickoffAgent",
    version="1.0.0",
)


class AskRequest(BaseModel):
    pregunta: str
    thread_id: Optional[str] = None


class AskResponse(BaseModel):
    respuesta: str
    thread_id: str
    herramientas: List[str]
    guardrails_entrada: Dict[str, bool]
    guardrail_salida: bool


def _extraer_herramientas(resultado: dict) -> List[str]:
    nombres = []
    for mensaje in resultado.get("messages", []):
        nombre = getattr(mensaje, "name", None)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
        for llamada in getattr(mensaje, "tool_calls", None) or []:
            valor = llamada.get("name") if isinstance(llamada, dict) else getattr(llamada, "name", None)
            if valor and valor not in nombres:
                nombres.append(valor)
    return nombres


@app.get("/health")
def health():
    return {
        "estado": "ok",
        "agente_inicializado": agent_executor is not None,
        "documentos_registrados": DOCUMENTOS_REGISTRADOS,
        "version": "1.0.0",
    }


@app.post("/ask", response_model=AskResponse)
def ask(solicitud: AskRequest):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agente sin inicializar. Configura una API key válida.")

    guardrails_entrada = validar_entrada(solicitud.pregunta)
    if entrada_bloqueada(guardrails_entrada):
        raise HTTPException(
            status_code=400,
            detail=f"Solicitud bloqueada por guardrails: {guardrails_entrada}",
        )

    thread_id = solicitud.thread_id or f"api_{uuid.uuid4().hex[:8]}"
    resultado = invocar_agente_seguro(
        {"messages": [("user", solicitud.pregunta)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    respuesta = resultado["messages"][-1].content
    return {
        "respuesta": respuesta,
        "thread_id": thread_id,
        "herramientas": _extraer_herramientas(resultado),
        "guardrails_entrada": guardrails_entrada,
        "guardrail_salida": validar_salida(respuesta),
    }


@app.get("/metrics")
def metrics():
    eventos = leer_logs(limite=1000)
    ejecuciones = [e for e in eventos if e.get("tipo") == "ejecucion"]
    latencias = [e["latencia_ms"] for e in ejecuciones if e.get("latencia_ms") is not None]
    errores = [e for e in ejecuciones if e.get("error")]
    herramientas = {}
    rutas = {}

    for ejecucion in ejecuciones:
        for nombre in ejecucion.get("herramientas", []):
            herramientas[nombre] = herramientas.get(nombre, 0) + 1
        ruta = ejecucion.get("ruta", "directa")
        rutas[ruta] = rutas.get(ruta, 0) + 1

    latencias_ordenadas = sorted(latencias)
    indice_p95 = int(len(latencias_ordenadas) * 0.95) if latencias_ordenadas else 0

    return {
        "total_ejecuciones": len(ejecuciones),
        "total_errores": len(errores),
        "tasa_error": round(len(errores) / len(ejecuciones), 4) if ejecuciones else 0,
        "latencia_promedio_ms": round(sum(latencias) / len(latencias), 2) if latencias else 0,
        "latencia_p95_ms": latencias_ordenadas[indice_p95] if latencias_ordenadas else 0,
        "rutas": rutas,
        "herramientas_mas_usadas": dict(
            sorted(herramientas.items(), key=lambda item: item[1], reverse=True)
        ),
        "tokens": summarize_usage({}),
    }


@app.get("/logs")
def logs(limite: int = 1000):
    """Devuelve los eventos registrados para que n8n los cargue en Supabase."""
    return {"total": len(leer_logs(limite=limite)), "eventos": leer_logs(limite=limite)}


@app.post("/eval")
def evaluar(limite: int = 15):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agente sin inicializar. Configura una API key válida.")

    from eval.run_evals import ejecutar_evaluacion

    try:
        return ejecutar_evaluacion(limite)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
