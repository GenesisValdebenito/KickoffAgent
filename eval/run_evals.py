"""Runner de evaluación de KickoffAgent.

Métricas calculadas:
    - Tool Call Accuracy: coincide el nombre de las herramientas esperadas.
    - Agent Goal Accuracy: juez LLM decide si la respuesta cumple la referencia.
    - Faithfulness y Answer Relevancy: jueces LLM sobre la ruta RAG.
    - Latencia por caso y consistencia de la tool financiera.

Uso:
    python -m eval.run_evals
    python -m eval.run_evals --limite 5
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv  # noqa: E402

from judges.juez import crear_juez as _crear_juez, proveedor_activo  # noqa: E402
from src.kickoff_agent import invocar_agente_seguro  # noqa: E402

load_dotenv(dotenv_path=BASE_DIR / ".env")

DATASET_PATH = BASE_DIR / "eval" / "dataset.json"
RESULTS_PATH = BASE_DIR / "eval" / "results.json"


def cargar_dataset() -> List[Dict[str, Any]]:
    datos = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return datos.get("casos", [])


def crear_juez():
    """Juez LLM. Prioriza OpenAI; el agente evaluado no se modifica."""
    juez = _crear_juez(max_tokens=180, timeout=60)
    print(f"Juez de evaluación: {proveedor_activo()}")
    return juez


def invocar_con_reintentos(funcion, descripcion: str, intentos: int = 5):
    """Reintenta ante límites de tasa u errores transitorios del proveedor."""
    ultimo_error = None
    for intento in range(intentos):
        try:
            return funcion()
        except Exception as exc:
            ultimo_error = exc
            if intento == intentos - 1:
                break
            mensaje = str(exc).lower()
            es_limite = "rate_limit" in mensaje or "rate limit" in mensaje or " 413 " in f" {mensaje} "
            espera = 65 if es_limite else min(30, 6 * (intento + 1))
            print(f"  Reintento {intento + 1}/{intentos - 1} para {descripcion} en {espera}s: {type(exc).__name__}")
            time.sleep(espera)
    raise ultimo_error


def invocar_juez(juez, prompt: str) -> str:
    return invocar_con_reintentos(lambda: juez.invoke(prompt).content, "juez").strip()


def extraer_herramientas(resultado: Dict[str, Any]) -> List[str]:
    nombres: List[str] = []
    for mensaje in resultado.get("messages", []):
        nombre = getattr(mensaje, "name", None)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
        for llamada in getattr(mensaje, "tool_calls", None) or []:
            valor = llamada.get("name") if isinstance(llamada, dict) else getattr(llamada, "name", None)
            if valor and valor not in nombres:
                nombres.append(valor)
    return nombres


def extraer_respuesta(resultado: Dict[str, Any]) -> str:
    for mensaje in reversed(resultado.get("messages", [])):
        contenido = getattr(mensaje, "content", "")
        if contenido and not getattr(mensaje, "tool_calls", None):
            return contenido
    return ""


def extraer_contexto_rag(resultado: Dict[str, Any]) -> str:
    fragmentos = []
    for mensaje in resultado.get("messages", []):
        if getattr(mensaje, "name", None) == "consultar_documentacion_proyecto":
            fragmentos.append(getattr(mensaje, "content", ""))
    return "\n\n".join(fragmentos)


def tool_call_accuracy(esperadas: List[str], obtenidas: List[str]) -> bool:
    return all(herramienta in obtenidas for herramienta in esperadas)


def _parsear_json(texto: str) -> Dict[str, Any]:
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?", "", limpio).strip()
    limpio = re.sub(r"```$", "", limpio).strip()
    inicio = limpio.find("{")
    fin = limpio.rfind("}")
    if inicio == -1 or fin == -1:
        return {}
    try:
        return json.loads(limpio[inicio:fin + 1])
    except json.JSONDecodeError:
        return {}


def juzgar_objetivo(pregunta: str, referencia: str, respuesta: str, juez, herramientas: List[str] = None) -> Tuple[bool, float, str]:
    herramientas_usadas = ", ".join(herramientas or []) or "ninguna"
    prompt = f"""Evalúa si la respuesta del agente cumple el objetivo de la pregunta.

Pregunta: {pregunta}
Respuesta esperada o hecho clave: {referencia}
Herramientas invocadas por el agente: {herramientas_usadas}
Respuesta del agente: {respuesta[:2500]}

Considera exitosa la invocación de una herramienta aunque el texto final no la nombre explícitamente.
Responde solo un JSON con:
{{"correcto": true o false, "score": número entre 0 y 1, "justificacion": texto breve en español}}"""
    salida = invocar_juez(juez, prompt)
    datos = _parsear_json(salida)
    return (
        bool(datos.get("correcto", False)),
        float(datos.get("score", 0.0)),
        str(datos.get("justificacion", "Sin justificación")),
    )


def juzgar_rag(pregunta: str, contexto: str, respuesta: str, juez) -> Tuple[Optional[float], Optional[float]]:
    """Faithfulness y relevancy solo aplican cuando hubo recuperación RAG."""
    if not contexto.strip():
        return None, None

    prompt_faith = f"""Evalúa si la respuesta está fundamentada en el contexto recuperado.
Devuelve solo un JSON con la clave "score", un número entre 0 y 1.

Contexto: {contexto[:3000]}
Respuesta: {respuesta[:2000]}"""
    prompt_rel = f"""Evalúa qué tan relevante es la respuesta para la pregunta.
Devuelve solo un JSON con la clave "score", un número entre 0 y 1.

Pregunta: {pregunta}
Respuesta: {respuesta[:2000]}"""

    faith = float(_parsear_json(invocar_juez(juez, prompt_faith)).get("score", 0.0))
    relev = float(_parsear_json(invocar_juez(juez, prompt_rel)).get("score", 0.0))
    return min(max(faith, 0.0), 1.0), min(max(relev, 0.0), 1.0)


def evaluar_caso(caso: Dict[str, Any], juez) -> Dict[str, Any]:
    inicio = time.perf_counter()
    error = None
    resultado = None

    try:
        resultado = invocar_con_reintentos(
            lambda: invocar_agente_seguro(
                {"messages": [("user", caso["pregunta"])]},
                config={"configurable": {"thread_id": f"eval_{caso['id']}_{os.getpid()}"}},
            ),
            f"agente caso {caso['id']}",
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    latencia_ms = round((time.perf_counter() - inicio) * 1000, 2)
    respuesta = extraer_respuesta(resultado or {})
    obtenidas = extraer_herramientas(resultado or {})
    esperadas = caso.get("herramientas_esperadas", [])
    contexto = extraer_contexto_rag(resultado or {})

    acierto_tools = tool_call_accuracy(esperadas, obtenidas)
    goal_correcto, goal_score, goal_justificacion = juzgar_objetivo(
        caso["pregunta"], caso.get("referencia", ""), respuesta, juez, obtenidas
    )
    faithfulness, relevancy = juzgar_rag(caso["pregunta"], contexto, respuesta, juez)

    cita = caso.get("debe_citar", "")
    cita_encontrada = bool(cita) and cita.lower() in respuesta.lower()

    return {
        "id": caso["id"],
        "categoria": caso.get("categoria"),
        "pregunta": caso["pregunta"],
        "referencia": caso.get("referencia"),
        "herramientas_esperadas": esperadas,
        "herramientas_obtenidas": obtenidas,
        "tool_call_accuracy": acierto_tools,
        "agent_goal_accuracy": goal_correcto,
        "agent_goal_score": round(goal_score, 3),
        "agent_goal_justificacion": goal_justificacion,
        "faithfulness": round(faithfulness, 3) if faithfulness is not None else None,
        "answer_relevancy": round(relevancy, 3) if relevancy is not None else None,
        "cita_esperada": cita,
        "cita_encontrada": cita_encontrada,
        "latencia_ms": latencia_ms,
        "respuesta": respuesta[:1000],
        "error": error,
    }


def _promedio(valores) -> float:
    validos = [v for v in valores if v is not None]
    return round(sum(validos) / len(validos), 4) if validos else 0.0


def resumir(resultados: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(resultados) or 1
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "juez": proveedor_activo(),
        "total_casos": len(resultados),
        "tool_call_accuracy": round(sum(r["tool_call_accuracy"] for r in resultados) / total, 4),
        "agent_goal_accuracy": round(sum(r["agent_goal_accuracy"] for r in resultados) / total, 4),
        "agent_goal_score_promedio": round(sum(r["agent_goal_score"] for r in resultados) / total, 4),
        "casos_con_contexto_rag": sum(1 for r in resultados if r["faithfulness"] is not None),
        "faithfulness_promedio": _promedio(r["faithfulness"] for r in resultados),
        "answer_relevancy_promedio": _promedio(r["answer_relevancy"] for r in resultados),
        "latencia_promedio_ms": round(sum(r["latencia_ms"] for r in resultados) / total, 2),
        "latencia_p95_ms": sorted(r["latencia_ms"] for r in resultados)[min(len(resultados) - 1, int(len(resultados) * 0.95))],
        "tasa_error": round(sum(1 for r in resultados if r["error"]) / total, 4),
        "resultados": resultados,
    }


def ejecutar_evaluacion(
    limite: Optional[int] = None,
    casos_ids: Optional[List[str]] = None,
    fusionar: bool = False,
) -> Dict[str, Any]:
    juez = crear_juez()
    todos = cargar_dataset()
    casos = todos

    if casos_ids:
        ids = set(casos_ids)
        casos = [caso for caso in casos if caso["id"] in ids]
    elif limite:
        casos = casos[:limite]

    nuevos = [evaluar_caso(caso, juez) for caso in casos]
    resultados = nuevos

    if fusionar and RESULTS_PATH.exists():
        anteriores = json.loads(RESULTS_PATH.read_text(encoding="utf-8")).get("resultados", [])
        mapa = {resultado["id"]: resultado for resultado in anteriores}
        for resultado in nuevos:
            mapa[resultado["id"]] = resultado
        resultados = [mapa[c["id"]] for c in todos if c["id"] in mapa]

    resumen = resumir(resultados)
    RESULTS_PATH.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa KickoffAgent con el dataset funcional")
    parser.add_argument("--limite", type=int, default=None, help="Cantidad máxima de casos")
    parser.add_argument("--caso", action="append", default=[], help="ID de caso a evaluar, repetible")
    parser.add_argument("--fusionar", action="store_true", help="Actualiza solo esos casos en results.json")
    args = parser.parse_args()

    resumen = ejecutar_evaluacion(args.limite, args.caso or None, args.fusionar)
    print(f"Casos evaluados: {resumen['total_casos']}")
    print(f"Tool Call Accuracy: {resumen['tool_call_accuracy']}")
    print(f"Agent Goal Accuracy: {resumen['agent_goal_accuracy']}")
    print(f"Faithfulness: {resumen['faithfulness_promedio']}")
    print(f"Answer Relevancy: {resumen['answer_relevancy_promedio']}")
    print(f"Latencia promedio: {resumen['latencia_promedio_ms']} ms")
    print(f"Resultados guardados en: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
