"""Módulo de Memoria Persistente para KickoffAgent.
Gestiona la persistencia de sesiones de conversación en disco (JSON),
permitiendo continuidad real entre reinicios del agente.
"""
import json
import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(thread_id: str) -> Path:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in thread_id)
    return SESSIONS_DIR / f"{safe_name}.json"


def guardar_sesion(thread_id: str, mensajes: list, metadata: Optional[dict] = None) -> None:
    datos = {
        "thread_id": thread_id,
        "ultima_actualizacion": datetime.datetime.now().isoformat(),
        "metadata": metadata or {},
        "mensajes": mensajes
    }
    path = _session_path(thread_id)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_sesion(thread_id: str) -> Optional[dict]:
    path = _session_path(thread_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def listar_sesiones() -> list:
    sesiones = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            datos = json.loads(f.read_text(encoding="utf-8"))
            sesiones.append({
                "thread_id": datos.get("thread_id", f.stem),
                "ultima_actualizacion": datos.get("ultima_actualizacion", "Desconocida"),
                "num_mensajes": len(datos.get("mensajes", [])),
                "documentos": datos.get("metadata", {}).get("documentos", [])
            })
        except Exception:
            continue
    return sesiones


def eliminar_sesion(thread_id: str) -> bool:
    path = _session_path(thread_id)
    if path.exists():
        path.unlink()
        return True
    return False


def mensajes_a_langchain(mensajes: list) -> list:
    resultado = []
    for m in mensajes:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in ("user", "human"):
            resultado.append(("user", content))
        elif role in ("ai", "assistant"):
            resultado.append(("assistant", content))
    return resultado


def mensajes_desde_state(state_messages: list) -> list:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    resultado = []
    for m in state_messages:
        if isinstance(m, HumanMessage):
            resultado.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            if m.content:
                resultado.append({"role": "ai", "content": m.content})
        elif isinstance(m, SystemMessage):
            pass
    return resultado
