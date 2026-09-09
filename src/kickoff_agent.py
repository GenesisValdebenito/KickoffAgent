import os
import sys
from pathlib import Path

# Configurar salida estándar a UTF-8 para evitar errores de codificación en Windows (cp1252)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Definición de rutas base del proyecto (resueltas desde src/)
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
PROMPTS_DIR = BASE_DIR / "prompts"
ENV_PATH = BASE_DIR / ".env"

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

from dotenv import load_dotenv
from typing import List, Optional
import numpy_financial as npf
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from langchain_groq import ChatGroq
try:
    # pyrefly: ignore [missing-import]
    from langchain_fastembed import FastEmbedEmbeddings
except ImportError:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=DeprecationWarning)
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.agents import create_agent

# ==============================================================================
# CONFIGURACIÓN DE LLM Y MODELOS
# ==============================================================================
# Cargar variables de entorno desde la raíz del proyecto
load_dotenv(dotenv_path=ENV_PATH)
# os.environ["GROQ_API_KEY"] debe estar definido en el archivo .env
llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0.0, max_tokens=800)
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# ==============================================================================
# 1. HERRAMIENTAS FINANCIERAS DETERMINISTAS (ZERO ALUCINACIONES)
# ==============================================================================

class FinancialEvalInput(BaseModel):
    inversion_inicial: float = Field(
        description="Inversión inicial requerida para el proyecto (valor positivo)."
    )
    flujos_caja: List[float] = Field(
        description="Lista secuencial de flujos netos proyectados por periodo (ej. años)."
    )
    tasa_descuento: float = Field(
        description="Tasa de descuento anual en formato decimal (ej: 0.12 para 12%)."
    )

@tool(args_schema=FinancialEvalInput)
def calcular_metricas_financieras(
    inversion_inicial: float,
    flujos_caja: List[float],
    tasa_descuento: float
) -> dict:
    """Calcula determinísticamente el VAN (NPV), TIR (IRR), ROI y Período de Recuperación (PRI).
    Úsalo obligatoriamente siempre que se requiera evaluar la viabilidad financiera de un proyecto."""
    
    # Serie de flujo de fondos con el egreso inicial en negativo
    cash_flows = [-abs(inversion_inicial)] + flujos_caja
    
    # 1. VAN (Valor Actual Neto)
    van = npf.npv(tasa_descuento, cash_flows)
    
    # 2. TIR (Tasa Interna de Retorno)
    try:
        tir = npf.irr(cash_flows)
        tir_pct = f"{round(tir * 100, 2)}%" if tir is not None else "No calculable"
    except Exception:
        tir_pct = "No convergente"

    # 3. ROI simple
    beneficio_neto = sum(flujos_caja) - abs(inversion_inicial)
    roi = (beneficio_neto / abs(inversion_inicial)) * 100

    # 4. Periodo de Recuperación de Inversión (PRI) no descontado
    acumulado = -abs(inversion_inicial)
    pri_periodos = "Supera el horizonte evaluado"
    for i, f in enumerate(flujos_caja, start=1):
        acumulado += f
        if acumulado >= 0:
            pri_periodos = f"{i} periodos"
            break

    return {
        "inversion_inicial": inversion_inicial,
        "van": round(float(van), 2),
        "tir": tir_pct,
        "roi_porcentual": f"{round(roi, 2)}%",
        "pri_estimado": pri_periodos,
        "conclusion_tecnica": (
            "Proyecto Financieramente Viable (VAN > 0)" if van > 0 
            else "Proyecto No Viable según criterio de VAN (VAN <= 0)"
        )
    }

# ==============================================================================
# 2. PIPELINE RAG (INGESTA, CHUNKING Y VECTOR STORE)
# ==============================================================================

def inicializar_vectorstore(pdf_paths: Optional[List[str]] = None) -> Chroma:
    """Carga documentos, aplica chunking con solapamiento y genera el Vector Store."""
    docs = []
    
    # Si se pasan rutas de PDF reales, se cargan; si no, se usan datos sintéticos de demostración
    if pdf_paths:
        for path in pdf_paths:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = BASE_DIR / path
            if file_path.exists():
                loader = PyPDFLoader(str(file_path))
                docs.extend(loader.load())
    
    # Chunking jerárquico optimizado para mantener contexto
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )
    
    if not docs:
        # Documentos sintéticos de prueba para simular actas de levantamiento
        from langchain_core.documents import Document
        docs = [
            Document(
                page_content="Acta Reunión 1: El cliente necesita un sistema web para gestión de inventario. "
                             "Presupuesto límite de inversión inicial: $12.000.000 CLP. "
                             "Proyección de ahorro anual: Año 1: $4.500.000, Año 2: $5.000.000, Año 3: $6.200.000. "
                             "Tasa de descuento exigida por gerencia: 10%.",
                metadata={"source": "Acta_Reunion_01.pdf", "fase": "finanzas"}
            ),
            Document(
                page_content="Especificación Técnica IEEE 830: RF-01: El sistema debe autenticar usuarios mediante OAuth2. "
                             "RF-02: El sistema debe generar reportes exportables en formato PDF y Excel en menos de 3 segundos. "
                             "RNF-01: La disponibilidad del servicio debe ser 99.9% en horario hábil.",
                metadata={"source": "Especificacion_IEEE830.pdf", "fase": "requerimientos"}
            )
        ]
        
    chunks = text_splitter.split_documents(docs)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="kickoff_agent_knowledge"
    )
    return vectorstore

# Instanciar el vectorstore y el retriever
vector_db = inicializar_vectorstore()
retriever = vector_db.as_retriever(search_kwargs={"k": 3})

@tool
def consultar_documentacion_proyecto(consulta: str) -> str:
    """Consulta la base de conocimiento vectorial del proyecto (actas, contratos, requerimientos IEEE 830).
    Devuelve los fragmentos más relevantes junto con sus fuentes y metadatos."""
    docs = retriever.invoke(consulta)
    if not docs:
        return "No se encontró información relevante en los documentos del proyecto."
    
    resultado = []
    for d in docs:
        fuente = d.metadata.get("source", "Desconocida")
        resultado.append(f"--- Fuente: {fuente} ---\n{d.page_content}")
    
    return "\n\n".join(resultado)

# ==============================================================================
# 3. CONSTRUCCIÓN DEL AGENTE ORQUESTADOR
# ==============================================================================

tools = [consultar_documentacion_proyecto, calcular_metricas_financieras]

system_prompt = """Eres 'KickoffAgent', un asistente senior de consultoría e ingeniería de software.
Tu misión es guiar la planificación estratégica, viabilidad financiera y levantamiento de requerimientos bajo IEEE 830.

REGLAS DE OPERACIÓN ESTRICTAS:
1. Grounding y Citas: Responde basándote ÚNICAMENTE en los documentos recuperados mediante 'consultar_documentacion_proyecto'. Siempre cita el archivo de origen (ej: [Acta_Reunion_01.pdf]).
2. Rigor Matemático: NUNCA calcules el VAN, TIR o flujos de caja manualmente. Siempre utiliza la herramienta 'calcular_metricas_financieras' extrayendo primero los datos necesarios.
3. Formato de Salida:
   - Para requerimientos: Estructura en formato IEEE 830 / Historias de Usuario (Como / Quiero / Para).
   - Para finanzas: Entrega una tabla comparativa con VAN, TIR, ROI y la recomendación técnica formal.
"""

agent_executor = create_agent(model=llm, tools=tools, system_prompt=system_prompt)

# ==============================================================================
# 4. EJECUCIÓN DE PRUEBA
# ==============================================================================

if __name__ == "__main__":
    console.print()
    console.print(Panel("[bold cyan]KickoffAgent[/bold cyan] — Agente Inteligente de Formulación de Proyectos", border_style="cyan"))
    console.print()

    # --- TEST 1: CONSULTA DE REQUERIMIENTOS CON RAG ---
    query_req = "¿Cuáles son los requerimientos funcionales aprobados y en qué documento se basan?"
    res_req = agent_executor.invoke({"messages": [("user", query_req)]})
    resp_req_text = res_req["messages"][-1].content
    console.print(Panel(Markdown(resp_req_text), title="TEST 1 — Consulta RAG", border_style="cyan"))

    console.print()
    console.rule("[bold cyan]────────────────────────────────────────────────────────────[/bold cyan]")
    console.print()

    # --- TEST 2: EVALUACIÓN FINANCIERA AUTOMATIZADA CON TOOL CALLING ---
    query_fin = "Revisa los documentos del proyecto, busca los datos de inversión y evalúa si es viable financieramente."
    res_fin = agent_executor.invoke({"messages": [("user", query_fin)]})
    resp_fin_text = res_fin["messages"][-1].content
    console.print(Panel(Markdown(resp_fin_text), title="TEST 2 — Evaluación Financiera", border_style="green"))
    console.print()

    # ==============================================================================
    # 5. MODO INTERACTIVO
    # ==============================================================================
    console.rule("[bold yellow]Modo Interactivo[/bold yellow]")
    console.print()
    console.print(Panel("Modo interactivo — escribe tu consulta o 'salir' para terminar", border_style="yellow"))
    console.print()

    while True:
        try:
            query = console.input("[bold yellow]> Consulta:[/bold yellow] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Sesión cerrada.[/cyan]")
            break

        clean_query = query.strip()
        if clean_query.lower() in ["salir", "exit"]:
            console.print("[cyan]Sesión cerrada.[/cyan]")
            break

        if not clean_query:
            continue

        try:
            res = agent_executor.invoke({"messages": [("user", clean_query)]})
            respuesta = res["messages"][-1].content
            console.print()
            console.print(Panel(Markdown(respuesta), title="KickoffAgent", border_style="cyan"))
            console.print()
        except Exception as e:
            console.print(f"[red]Error al procesar la consulta: {e}[/red]")
