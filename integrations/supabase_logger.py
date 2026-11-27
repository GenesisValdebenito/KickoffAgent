"""Carga de logs y resultados a Supabase mediante REST.

Requiere en .env:
    SUPABASE_URL=https://<proyecto>.supabase.co
    SUPABASE_SERVICE_KEY=<service_role_key>

Uso:
    python -m integrations.supabase_logger
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

from observability.logger import leer_logs  # noqa: E402

URL = os.getenv("SUPABASE_URL", "").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def _headers() -> Dict[str, str]:
    return {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def configurado() -> bool:
    return bool(URL and KEY)


def insertar_tabla(tabla: str, filas: List[Dict[str, Any]]) -> int:
    if not configurado():
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en .env")
    if not filas:
        return 0

    respuesta = requests.post(
        f"{URL}/rest/v1/{tabla}",
        headers=_headers(),
        json=filas,
        timeout=30,
    )
    respuesta.raise_for_status()
    return len(filas)


def cargar_logs(limite: int = 100) -> int:
    eventos = leer_logs(limite=limite)
    filas = []
    for evento in eventos:
        filas.append({
            "trace_id": evento.get("trace_id"),
            "thread_id": evento.get("thread_id"),
            "tipo": evento.get("tipo"),
            "timestamp": evento.get("timestamp"),
            "ruta": evento.get("ruta"),
            "herramientas": evento.get("herramientas", []),
            "chunks_recuperados": evento.get("chunks_recuperados", 0),
            "latencia_ms": evento.get("latencia_ms"),
            "tokens": evento.get("tokens", {}),
            "error": evento.get("error"),
            "salida": evento.get("salida", "")[:2000],
        })
    return insertar_tabla("logs", filas)


def cargar_resultados_evaluacion() -> int:
    ruta = BASE_DIR / "eval" / "results.json"
    if not ruta.exists():
        return 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    resumen = {k: v for k, v in datos.items() if k != "resultados"}
    return insertar_tabla("evals", [{
        "fecha": datos.get("timestamp", ""),
        "resumen": resumen,
        "detalle": datos.get("resultados", []),
    }])


def main() -> None:
    if not configurado():
        print("Supabase no configurado. Definí SUPABASE_URL y SUPABASE_SERVICE_KEY en .env.")
        return
    print(f"Logs cargados: {cargar_logs()}")
    print(f"Evaluaciones cargadas: {cargar_resultados_evaluacion()}")


if __name__ == "__main__":
    main()
