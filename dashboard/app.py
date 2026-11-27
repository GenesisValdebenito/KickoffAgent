"""Dashboard Streamlit de KickoffAgent.

Ejecución:
    streamlit run dashboard/app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from observability.logger import LOG_FILE, leer_logs  # noqa: E402

st.set_page_config(page_title="KickoffAgent Observability", layout="wide")
st.title("KickoffAgent — Panel de observabilidad")
st.caption(f"Fuente de datos: {LOG_FILE.relative_to(BASE_DIR)}")

eventos = leer_logs(limite=1000)
ejecuciones = [e for e in eventos if e.get("tipo") == "ejecucion"]

if not ejecuciones:
    st.warning("Todavía no hay ejecuciones registradas. Corre el agente o el runner de evaluación.")
    st.stop()

latencias = [e.get("latencia_ms", 0) for e in ejecuciones]
errores = [e for e in ejecuciones if e.get("error")]
latencias_ordenadas = sorted(latencias)
p95 = latencias_ordenadas[min(len(latencias_ordenadas) - 1, int(len(latencias_ordenadas) * 0.95))]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ejecuciones", len(ejecuciones))
col2.metric("Errores", len(errores))
col3.metric("Latencia promedio", f"{round(sum(latencias) / len(latencias), 1)} ms")
col4.metric("Latencia p95", f"{p95} ms")

rutas = {}
herramientas = {}
for evento in ejecuciones:
    ruta = evento.get("ruta", "directa")
    rutas[ruta] = rutas.get(ruta, 0) + 1
    for nombre in evento.get("herramientas", []):
        herramientas[nombre] = herramientas.get(nombre, 0) + 1

col_izq, col_der = st.columns(2)
with col_izq:
    st.subheader("Rutas ejecutadas")
    st.bar_chart(pd.Series(rutas, name="cantidad"))

with col_der:
    st.subheader("Herramientas invocadas")
    st.bar_chart(pd.Series(herramientas, name="cantidad"))

st.subheader("Detalle de ejecuciones")
rutas_disponibles = ["todas"] + sorted(rutas)
filtro = st.selectbox("Filtrar por ruta", rutas_disponibles)
filtradas = ejecuciones if filtro == "todas" else [e for e in ejecuciones if e.get("ruta") == filtro]

tabla = pd.DataFrame([
    {
        "timestamp": e.get("timestamp"),
        "thread_id": e.get("thread_id"),
        "ruta": e.get("ruta"),
        "herramientas": ", ".join(e.get("herramientas", [])),
        "chunks": e.get("chunks_recuperados", 0),
        "latencia_ms": e.get("latencia_ms"),
        "error": e.get("error") or "",
    }
    for e in filtradas
])
st.dataframe(tabla, width="stretch")

st.subheader("Registro crudo")
with st.expander("Ver JSONL completo"):
    st.code("\n".join(
        json.dumps(e, ensure_ascii=False) for e in filtradas
    ), language="json")
