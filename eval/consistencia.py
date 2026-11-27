"""Prueba de consistencia: repetir casos y medir varianza.

Uso:
    python -m eval.consistencia
    python -m eval.consistencia --caso ari_001 --fusionar
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from eval.run_evals import (  # noqa: E402
    DATASET_PATH,
    extraer_herramientas,
    extraer_respuesta,
    invocar_con_reintentos,
    tool_call_accuracy,
)
from src.kickoff_agent import invocar_agente_seguro  # noqa: E402

RESULTADO_PATH = BASE_DIR / "eval" / "consistencia.json"
CASOS = ["fin_003", "rag_003", "ari_001"]
REPETICIONES = 5


def evaluar_caso(caso: dict, caso_id: str) -> dict:
    latencias = []
    aciertos = []
    respuestas = []
    fallos = 0
    marca = str(int(time.time()))

    for repeticion in range(REPETICIONES):
        inicio = time.perf_counter()
        try:
            salida = invocar_con_reintentos(
                lambda: invocar_agente_seguro(
                    {"messages": [("user", caso["pregunta"])]},
                    config={"configurable": {"thread_id": f"cons_{caso_id}_{repeticion}_{marca}"}},
                ),
                f"consistencia {caso_id}",
                intentos=2,
            )
            respuesta = extraer_respuesta(salida)
            obtenidas = extraer_herramientas(salida)
            acierto = tool_call_accuracy(caso.get("herramientas_esperadas", []), obtenidas)
            latencias.append(round((time.perf_counter() - inicio) * 1000, 2))
        except Exception as exc:
            fallos += 1
            respuesta = ""
            acierto = False
            print(f"  Error en {caso_id} repetición {repeticion}: {exc}")

        aciertos.append(acierto)
        respuestas.append(respuesta[:500])

    return {
        "id": caso_id,
        "pregunta": caso["pregunta"],
        "repeticiones": REPETICIONES,
        "repeticiones_exitosas": len(latencias),
        "fallos": fallos,
        "tool_call_accuracy": round(sum(aciertos) / len(aciertos), 4),
        "latencia_promedio_ms": round(statistics.mean(latencias), 2) if latencias else 0,
        "latencia_desviacion_ms": round(statistics.pstdev(latencias), 2) if latencias else 0,
        "latencia_min_ms": min(latencias) if latencias else 0,
        "latencia_max_ms": max(latencias) if latencias else 0,
        "respuestas_distintas": len(set(respuestas)),
        "respuestas": respuestas,
    }


def ejecutar(casos_ids: Optional[List[str]] = None, fusionar: bool = False) -> dict:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    por_id = {caso["id"]: caso for caso in dataset.get("casos", [])}
    ids = casos_ids or CASOS
    nuevos = [evaluar_caso(por_id[caso_id], caso_id) for caso_id in ids if caso_id in por_id]

    resultados = nuevos
    if fusionar and RESULTADO_PATH.exists():
        anteriores = json.loads(RESULTADO_PATH.read_text(encoding="utf-8")).get("casos", [])
        mapa = {resultado["id"]: resultado for resultado in anteriores}
        for resultado in nuevos:
            if resultado["fallos"] == REPETICIONES and resultado["id"] in mapa:
                print(f"  Se conserva el resultado anterior de {resultado['id']}: todos los reintentos fallaron")
                continue
            mapa[resultado["id"]] = resultado
        resultados = [mapa[caso_id] for caso_id in CASOS if caso_id in mapa]

    resumen = {
        "casos": resultados,
        "consistencia_promedio": round(
            sum(r["tool_call_accuracy"] for r in resultados) / len(resultados), 4
        ) if resultados else 0,
    }
    RESULTADO_PATH.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    for resultado in nuevos:
        print(f"{resultado['id']}: accuracy {resultado['tool_call_accuracy']}, "
              f"desviación {resultado['latencia_desviacion_ms']} ms, fallos {resultado['fallos']}")
    return resumen


def main() -> None:
    parser = argparse.ArgumentParser(description="Consistencia de KickoffAgent")
    parser.add_argument("--caso", action="append", default=[], help="ID de caso a repetir")
    parser.add_argument("--fusionar", action="store_true", help="Actualiza solo esos casos")
    args = parser.parse_args()
    ejecutar(args.caso or None, args.fusionar)


if __name__ == "__main__":
    main()
