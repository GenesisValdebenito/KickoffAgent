"""API FastAPI para KickoffAgent.

Endpoints:
    GET  /health
    POST /ask
    GET  /metrics
    POST /eval

Ejecución:
    uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
"""

import json
import sys
import uuid
from pathlib import Path
from typing import List, Optional

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

DATASET_PATH = BASE_DIR / "eval" / "dataset.json"
RESULTS_PATH = BASE_DIR / "eval" / "results.json"

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

    thread_id = solicitud.thread_id or f"api_{uuid.uuid4().hex[:8]}"
    resultado = invocar_agente_seguro(
        {"messages": [("user", solicitud.pregunta)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return {
        "respuesta": resultado["messages"][-1].content,
        "thread_id": thread_id,
        "herramientas": _extraer_herramientas(resultado),
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


@app.post("/eval")
def evaluar(limite: int = 15):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agente sin inicializar. Configura una API key válida.")

    if not DATASET_PATH.exists():
        raise HTTPException(status_code=404, detail="No se encontró eval/dataset.json")

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    casos = dataset.get("casos", [])[:limite]
    resultados = []

    for caso in casos:
        thread_id = f"eval_{caso['id']}_{uuid.uuid4().hex[:6]}"
        try:
            resultado = invocar_agente_seguro(
                {"messages": [("user", caso["pregunta"])]},
                config={"configurable": {"thread_id": thread_id}},
            )
            obtenidas = _extraer_herramientas(resultado)
            esperadas = caso.get("herramientas_esperadas", [])
            acierto = all(h in obtenidas for h in esperadas)
            respuesta = resultado["messages"][-1].content
            error = None
        except Exception as exc:
            obtenidas = []
            acierto = False
            respuesta = ""
            error = f"{type(exc).__name__}: {exc}"

        resultados.append({
            "id": caso["id"],
            "categoria": caso.get("categoria"),
            "herramientas_esperadas": esperadas,
            "herramientas_obtenidas": obtenidas,
            "tool_call_accuracy": acierto,
            "referencia": caso.get("referencia"),
            "respuesta": respuesta[:1000],
            "error": error,
        })

    total = len(resultados)
    correctos = sum(1 for r in resultados if r["tool_call_accuracy"])
    resumen = {
        "total_casos": total,
        "casos_correctos": correctos,
        "tool_call_accuracy": round(correctos / total, 4) if total else 0,
        "resultados": resultados,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen
