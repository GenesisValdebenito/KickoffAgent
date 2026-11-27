"""Registro estructurado de ejecuciones del agente en formato JSONL."""

import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "agent_logs.jsonl"

MAX_TEXTO = 2000


def _recortar(texto: Any) -> str:
    valor = str(texto)
    if len(valor) > MAX_TEXTO:
        return valor[:MAX_TEXTO] + "... [truncado]"
    return valor


def _normalizar_entrada(mensajes: Iterable[Any]) -> List[Dict[str, str]]:
    normalizados = []
    for mensaje in mensajes or []:
        if isinstance(mensaje, tuple) and len(mensaje) >= 2:
            normalizados.append({"role": str(mensaje[0]), "content": _recortar(mensaje[1])})
        elif isinstance(mensaje, dict):
            normalizados.append({
                "role": str(mensaje.get("role", "user")),
                "content": _recortar(mensaje.get("content", "")),
            })
        else:
            normalizados.append({
                "role": str(getattr(mensaje, "type", "unknown")),
                "content": _recortar(getattr(mensaje, "content", mensaje)),
            })
    return normalizados


def _nombres_herramientas(mensajes: Iterable[Any]) -> List[str]:
    nombres = []
    for mensaje in mensajes or []:
        nombre = getattr(mensaje, "name", None)
        if nombre and nombre not in nombres:
            nombres.append(nombre)
        llamadas = getattr(mensaje, "tool_calls", None) or []
        for llamada in llamadas:
            if isinstance(llamada, dict):
                nombre_llamada = llamada.get("name")
            else:
                nombre_llamada = getattr(llamada, "name", None)
            if nombre_llamada and nombre_llamada not in nombres:
                nombres.append(nombre_llamada)
    return nombres


def _definir_ruta(herramientas: List[str]) -> str:
    if "calcular_metricas_financieras" in herramientas and "consultar_documentacion_proyecto" in herramientas:
        return "mixta"
    if "calcular_metricas_financieras" in herramientas:
        return "financiera"
    if "consultar_documentacion_proyecto" in herramientas:
        return "rag"
    herramientas_persistencia = {
        "guardar_informe_kickoff",
        "editar_nota_kickoff",
        "eliminar_nota_kickoff",
        "exportar_resumen_sesion",
    }
    if any(h in herramientas_persistencia for h in herramientas):
        return "persistencia"
    return "directa"


def registrar_evento(tipo: str, datos: Dict[str, Any]) -> None:
    """Añade un evento genérico al archivo JSONL."""
    registro = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "trace_id": str(uuid.uuid4()),
        "tipo": tipo,
        **datos,
    }
    with LOG_FILE.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def registrar_ejecucion(
    thread_id: str,
    entrada: Iterable[Any],
    resultado: Optional[Dict[str, Any]],
    latencia_ms: float,
    error: Optional[str] = None,
    tokens: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Registra una invocación completa del grafo."""
    mensajes = (resultado or {}).get("messages", [])
    herramientas = _nombres_herramientas(mensajes)
    chunks = 0
    salida = ""

    for mensaje in mensajes:
        nombre = getattr(mensaje, "name", None)
        contenido = getattr(mensaje, "content", "")
        if nombre == "consultar_documentacion_proyecto":
            chunks += contenido.count("--- Fuente:")
        tiene_llamadas = bool(getattr(mensaje, "tool_calls", None))
        if not nombre and not tiene_llamadas and contenido:
            salida = _recortar(contenido)

    registro = {
        "thread_id": thread_id,
        "ruta": _definir_ruta(herramientas),
        "entrada": _normalizar_entrada(entrada),
        "herramientas": herramientas,
        "chunks_recuperados": chunks,
        "salida": salida,
        "latencia_ms": round(float(latencia_ms), 2),
        "tokens": tokens or {"prompt": 0, "completion": 0, "total": 0},
        "error": error,
    }
    registrar_evento("ejecucion", registro)
    return registro


def leer_logs(limite: int = 50) -> List[Dict[str, Any]]:
    """Devuelve las últimas entradas del log."""
    if not LOG_FILE.exists():
        return []
    lineas = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(linea) for linea in lineas[-limite:] if linea.strip()]
