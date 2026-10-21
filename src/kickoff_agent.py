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
sys.path.insert(0, str(BASE_DIR))
DOCS_DIR = BASE_DIR / "docs"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ENV_PATH = BASE_DIR / ".env"

from langgraph.checkpoint.memory import MemorySaver

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
groq_api_key = os.environ.get("GROQ_API_KEY") or "dummy_key_for_testing"
llm = ChatGroq(
    model="qwen/qwen3.8-27b",
    temperature=0.0,
    max_tokens=800,
    api_key=groq_api_key,
    max_retries=3,
    timeout=60
)
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# Importación de herramientas modulares desde src/tools.py (estilo canónico del curso)
from src.tools import (
    calcular_metricas_financieras,
    guardar_informe_kickoff,
    sumar,
    restar,
    multiplicar,
    dividir
)

# ==============================================================================
# 2. PIPELINE RAG (INGESTA, CHUNKING Y VECTOR STORE - MEMORIA LARGO PLAZO)
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
# 4. CONSTRUCCIÓN DEL AGENTE ORQUESTADOR CON LANGGRAPH (ESTRUCTURA DE NODOS Y ARISTAS)
# ==============================================================================

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage

# 1. Integración de herramientas: consulta documental, finanzas, persistencia y aritmética
tools = [
    consultar_documentacion_proyecto,
    calcular_metricas_financieras,
    guardar_informe_kickoff,
    sumar,
    restar,
    multiplicar,
    dividir
]

# Vincular las herramientas al LLM (Tool Binding)
llm_with_tools = llm.bind_tools(tools)

# 2. Definición del Estado del Grafo (AgentState)
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 3. Prompt de Sistema Modular (Estrategia de Planificación y Reglas)
from src.prompts import AGENT_SYSTEM_PROMPT

# 4. Nodos del Grafo
def call_model(state: AgentState) -> AgentState:
    """Nodo 'agent': invoca al LLM inyectando el system prompt y la historia de mensajes."""
    system = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}

tool_node = ToolNode(tools)

# 5. Función de decisión (Arista Condicional)
def should_continue(state: AgentState) -> str:
    """Evalúa si el modelo decidió invocar alguna herramienta o responder directamente."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# 6. Ensamblado del Grafo (StateGraph, Nodos y Aristas)
workflow = StateGraph(AgentState)

# Registrar nodos
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Configurar punto de entrada y aristas
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)
workflow.add_edge("tools", "agent")

# 7. Memoria de Corto Plazo y Compilación
memory_saver = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory_saver)

# ==============================================================================
# 5. EJECUCIÓN DE PRUEBA Y DEMOSTRACIÓN DE MEMORIA Y ORQUESTACIÓN
# ==============================================================================

if __name__ == "__main__":
    console.print()
    console.print(Panel("[bold cyan]KickoffAgent[/bold cyan] — Agente Inteligente de Formulación de Proyectos", border_style="cyan"))
    console.print()

    # Identificador de sesión para el hilo de memoria conversacional
    session_config = {"configurable": {"thread_id": "sesion_kickoff_demo"}}

    # --- TEST 1: CONSULTA DE REQUERIMIENTOS CON RAG ---
    query_req = "¿Cuáles son los requerimientos funcionales aprobados y en qué documento se basan?"
    res_req = agent_executor.invoke({"messages": [("user", query_req)]}, config=session_config)
    resp_req_text = res_req["messages"][-1].content
    console.print(Panel(Markdown(resp_req_text), title="TEST 1 — Consulta RAG", border_style="cyan"))

    console.print()
    console.rule("[bold cyan]────────────────────────────────────────────────────────────[/bold cyan]")
    console.print()

    # --- TEST 2: EVALUACIÓN FINANCIERA AUTOMATIZADA CON TOOL CALLING ---
    query_fin = "Revisa los documentos del proyecto, busca los datos de inversión y evalúa si es viable financieramente."
    res_fin = agent_executor.invoke({"messages": [("user", query_fin)]}, config=session_config)
    resp_fin_text = res_fin["messages"][-1].content
    console.print(Panel(Markdown(resp_fin_text), title="TEST 2 — Evaluación Financiera", border_style="green"))
    console.print()

    console.rule("[bold cyan]────────────────────────────────────────────────────────────[/bold cyan]")
    console.print()

    # --- TEST 3: COMPROBACIÓN DE MEMORIA Y HERRAMIENTA DE ESCRITURA ---
    query_write = "Tomando en cuenta la viabilidad que acabas de calcular en la consulta anterior, redacta un dictamen formal y guárdalo en un archivo llamado 'dictamen_kickoff.md'."
    res_write = agent_executor.invoke({"messages": [("user", query_write)]}, config=session_config)
    resp_write_text = res_write["messages"][-1].content
    console.print(Panel(Markdown(resp_write_text), title="TEST 3 — Memoria y Escritura en Disco", border_style="magenta"))
    console.print()

    # ==============================================================================
    # 6. MODO INTERACTIVO
    # ==============================================================================
    console.rule("[bold yellow]Modo Interactivo (Memoria Activa)[/bold yellow]")
    console.print()
    console.print(Panel("Modo interactivo — escribe tu consulta o 'salir' para terminar (El agente recuerda toda la conversación)", border_style="yellow"))
    console.print()

    interactive_config = {"configurable": {"thread_id": "sesion_interactiva_usuario"}}

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
            res = agent_executor.invoke({"messages": [("user", clean_query)]}, config=interactive_config)
            respuesta = res["messages"][-1].content
            console.print()
            console.print(Panel(Markdown(respuesta), title="KickoffAgent", border_style="cyan"))
            console.print()
        except Exception as e:
            console.print(f"[red]Error al procesar la consulta: {e}[/red]")
