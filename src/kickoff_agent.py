import os
import sys
from pathlib import Path

# Configurar salida estándar a UTF-8 para evitar errores de codificación en Windows (cp1252)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Suprimir advertencias y retardos por symlinks de huggingface en Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

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
import subprocess
import time
from typing import List, Optional, TypedDict, Annotated, Union

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

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
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

# Importación de herramientas modulares desde src/tools.py
from src.tools import (
    calcular_metricas_financieras,
    guardar_informe_kickoff,
    editar_nota_kickoff,
    eliminar_nota_kickoff,
    exportar_resumen_sesion,
    sumar,
    restar,
    multiplicar,
    dividir
)
from src.prompts import AGENT_SYSTEM_PROMPT
from src.memory import (
    guardar_sesion,
    cargar_sesion,
    listar_sesiones,
    eliminar_sesion,
    mensajes_a_langchain,
    mensajes_desde_state,
    SESSIONS_DIR
)

# Cargar variables de entorno desde la raíz del proyecto
load_dotenv(dotenv_path=ENV_PATH)

# ==============================================================================
# 2. PIPELINE RAG (INGESTA, CHUNKING Y VECTOR STORE - MEMORIA LARGO PLAZO)
# ==============================================================================

embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

DOCUMENTOS_REGISTRADOS: List[str] = ["Acta_Reunion_01.pdf", "Especificacion_IEEE830.pdf"]

def cargar_documentos_desde_ruta(ruta: Union[str, Path]) -> list:
    """Carga documentos desde una ruta de archivo o directorio.
    Soporta .pdf (PyPDFLoader), .txt, .md, .markdown, .csv y .json."""
    from langchain_core.documents import Document
    p = Path(ruta)
    if not p.is_absolute():
        p = BASE_DIR / ruta

    if not p.exists():
        return []

    archivos: List[Path] = []
    if p.is_dir():
        for patron in ["*.pdf", "*.txt", "*.md", "*.markdown", "*.csv", "*.json"]:
            archivos.extend(p.glob(patron))
    else:
        archivos = [p]

    documentos_cargados = []
    for arch in archivos:
        try:
            ext = arch.suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(str(arch))
                paginas = loader.load()
                for pag in paginas:
                    pag.metadata["source"] = arch.name
                documentos_cargados.extend(paginas)
            elif ext in [".txt", ".md", ".markdown", ".csv", ".json"]:
                texto = arch.read_text(encoding="utf-8", errors="ignore")
                if texto.strip():
                    documentos_cargados.append(Document(
                        page_content=texto,
                        metadata={"source": arch.name, "tipo": ext}
                    ))
        except Exception as e:
            console.print(f"[yellow]⚠ Error al procesar {arch.name}: {e}[/yellow]")

    return documentos_cargados

def inicializar_vectorstore(pdf_paths: Optional[List[str]] = None) -> Chroma:
    """Carga documentos, aplica chunking con solapamiento y genera el Vector Store."""
    docs = []
    
    if pdf_paths:
        for path in pdf_paths:
            docs.extend(cargar_documentos_desde_ruta(path))
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )
    
    if not docs:
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

vector_db = inicializar_vectorstore()
retriever = vector_db.as_retriever(search_kwargs={"k": 4})

def agregar_documento_al_agente(ruta: Union[str, Path]) -> int:
    """Indexa dinámicamente un documento o directorio en el vectorstore activo."""
    global vector_db, retriever, DOCUMENTOS_REGISTRADOS
    docs = cargar_documentos_desde_ruta(ruta)
    if not docs:
        return 0
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )
    chunks = text_splitter.split_documents(docs)
    vector_db.add_documents(chunks)
    retriever = vector_db.as_retriever(search_kwargs={"k": 4})
    
    p = Path(ruta)
    nombre = p.name if not p.is_dir() else f"Carpeta ({p.name})"
    if nombre not in DOCUMENTOS_REGISTRADOS:
        DOCUMENTOS_REGISTRADOS.append(nombre)
        
    return len(chunks)

@tool
def consultar_documentacion_proyecto(consulta: str) -> str:
    """Consulta la base de conocimiento vectorial del proyecto (documentos ingresados, actas, contratos, requerimientos IEEE 830).
    Devuelve los fragmentos más relevantes junto con sus fuentes, páginas y metadatos."""
    docs = retriever.invoke(consulta)
    if not docs:
        return "No se encontró información relevante en los documentos del proyecto."
    
    resultado = []
    for d in docs:
        fuente = d.metadata.get("source", "Desconocida")
        pagina = d.metadata.get("page", None)
        header = f"--- Fuente: {Path(fuente).name}" + (f" (Pág. {pagina + 1})" if pagina is not None else "") + " ---"
        resultado.append(f"{header}\n{d.page_content}")
    
    return "\n\n".join(resultado)


# ==============================================================================
# 3. LISTA DE HERRAMIENTAS Y ENSAMBLADO DEL GRAFO LANGGRAPH
# ==============================================================================

tools = [
    consultar_documentacion_proyecto,
    calcular_metricas_financieras,
    guardar_informe_kickoff,
    editar_nota_kickoff,
    eliminar_nota_kickoff,
    exportar_resumen_sesion,
    sumar,
    restar,
    multiplicar,
    dividir
]

tool_node = ToolNode(tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def should_continue(state: AgentState) -> str:
    """Evalúa si el modelo decidió invocar alguna herramienta o responder directamente."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

def compilar_agente(chat_model):
    """Compila el grafo de LangGraph con el modelo LLM especificado."""
    bound_model = chat_model.bind_tools(tools)

    def call_model(state: AgentState) -> AgentState:
        system = SystemMessage(content=AGENT_SYSTEM_PROMPT)
        response = bound_model.invoke([system] + state["messages"])
        return {"messages": [response]}

    workflow_graph = StateGraph(AgentState)
    workflow_graph.add_node("agent", call_model)
    workflow_graph.add_node("tools", tool_node)
    workflow_graph.set_entry_point("agent")
    workflow_graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow_graph.add_edge("tools", "agent")
    
    memory_saver = MemorySaver()
    return workflow_graph.compile(checkpointer=memory_saver)

def es_api_key_valida(key: Optional[str]) -> bool:
    """Verifica si la API key tiene el formato oficial de Groq (gsk_...) o de OpenAI (sk-...)."""
    if not key:
        return False
    key_clean = key.strip()
    return (key_clean.startswith("gsk_") and len(key_clean) > 15) or (key_clean.startswith("sk-") and len(key_clean) > 20)


def obtener_llm_activo(groq_key: Optional[str] = None):
    """Retorna ChatGroq o ChatOpenAI. Si no hay credenciales, lanza un error explícito."""
    g_key = groq_key or os.environ.get("GROQ_API_KEY", "").strip()
    if g_key.startswith("gsk_") and len(g_key) > 15:
        return ChatGroq(
            model="qwen/qwen3.8-27b",
            temperature=0.0,
            max_tokens=800,
            api_key=g_key,
            max_retries=3,
            timeout=60
        )

    o_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not o_key and g_key.startswith("sk-"):
        o_key = g_key
    if o_key.startswith("sk-") and len(o_key) > 20:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=800,
                api_key=o_key,
                max_retries=2,
                timeout=30
            )
        except Exception:
            pass

    raise RuntimeError(
        "No se detectó una API key válida. Configura GROQ_API_KEY (gsk_...) "
        "u OPENAI_API_KEY (sk-...) en el archivo .env antes de ejecutar el agente."
    )


# Instancia global. Si no hay credenciales, el import no falla: el agente queda sin inicializar.
groq_api_key = os.environ.get("GROQ_API_KEY", "").strip()
try:
    llm = obtener_llm_activo(groq_api_key)
    llm_with_tools = llm.bind_tools(tools)
    agent_executor = compilar_agente(llm)
except RuntimeError:
    llm = None
    llm_with_tools = None
    agent_executor = None


def invocar_agente_seguro(messages_payload, config):
    """Invoca el grafo y registra la ejecución. Sin fallback a modo demostración."""
    if agent_executor is None:
        raise RuntimeError(
            "El agente no está inicializado. Configura una API key válida en .env "
            "y vuelve a ejecutar."
        )

    from observability.logger import registrar_ejecucion

    inicio = time.perf_counter()
    resultado = None
    error = None
    try:
        resultado = agent_executor.invoke(messages_payload, config=config)
        return resultado
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        latencia_ms = round((time.perf_counter() - inicio) * 1000, 2)
        registrar_ejecucion(
            thread_id=config.get("configurable", {}).get("thread_id", "sin_thread"),
            entrada=messages_payload,
            resultado=resultado,
            latencia_ms=latencia_ms,
            error=error,
        )


# 4. EJECUCIÓN PRINCIPAL Y MODO INTERACTIVO
# ==============================================================================

if __name__ == "__main__":
    console.print()
    console.print(Panel("[bold cyan]KickoffAgent[/bold cyan] — Agente Inteligente de Formulación de Proyectos", border_style="cyan"))
    console.print()

    if "--test" in sys.argv:
        raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v"]))

    # Comprobación de API Key. No existe modo demostración.
    current_key = os.environ.get("GROQ_API_KEY", "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
    if not es_api_key_valida(current_key):
        console.print(Panel(
            "[bold yellow]⚠ Configuración de conectividad[/bold yellow]\n\n"
            "No se detectó una API key válida. Ingresa una clave de Groq (gsk_...) "
            "o de OpenAI (sk-...) para continuar.",
            border_style="yellow"
        ))
        try:
            opcion = console.input("[bold yellow]> API key: [/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            opcion = ""

        if not es_api_key_valida(opcion):
            console.print("[bold red]✗ No se puede iniciar el agente sin una API key válida.[/bold red]")
            raise SystemExit(1)

        if opcion.startswith("gsk_"):
            ENV_PATH.write_text(f"GROQ_API_KEY={opcion}\n", encoding="utf-8")
            os.environ["GROQ_API_KEY"] = opcion
        else:
            ENV_PATH.write_text(f"OPENAI_API_KEY={opcion}\n", encoding="utf-8")
            os.environ["OPENAI_API_KEY"] = opcion

        llm = obtener_llm_activo(opcion)
        agent_executor = compilar_agente(llm)
        console.print("[bold green]✓ Clave API configurada y guardada en .env.[/bold green]\n")
    else:
        if agent_executor is None:
            llm = obtener_llm_activo(current_key)
            agent_executor = compilar_agente(llm)
        nombre_modelo = getattr(llm, "model_name", "qwen/qwen3.8-27b")
        console.print(f"[bold green]✓ Conexión activa con el proveedor LLM (Modelo: {nombre_modelo}).[/bold green]\n")

    # ===========================================================================
    # SELECCIÓN DE SESIÓN: Continuar anterior o nueva
    # ===========================================================================
    sesiones_previas = listar_sesiones()
    thread_id = None

    if sesiones_previas:
        console.print()
        console.print(Panel(
            "[bold cyan]Sesión Previa Detectada[/bold cyan]\n\n"
            f"Se encontraron [bold]{len(sesiones_previas)}[/bold] sesión(es) guardada(s).\n\n"
            "[bold green]1.[/bold green] Continuar la última conversación\n"
            "[bold yellow]2.[/bold yellow] Nueva conversación (sesión limpia)\n"
            "[bold red]3.[/bold red] Ver todas las sesiones guardadas",
            border_style="cyan",
            title="¿Qué deseas hacer?"
        ))
        try:
            opcion_sesion = console.input("[bold yellow]> Ingresa 1, 2 o 3: [/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            opcion_sesion = "2"

        if opcion_sesion == "1":
            # Continuar la sesión más reciente
            sesion_reciente = sesiones_previas[0]
            thread_id = sesion_reciente["thread_id"]
            datos_sesion = cargar_sesion(thread_id)
            num_msgs = sesion_reciente["num_mensajes"]
            ts = sesion_reciente["ultima_actualizacion"][:16].replace("T", " ")
            console.print(f"[bold green]✓ Cargada sesión anterior: '{thread_id}' ({num_msgs} mensajes, última actividad: {ts})[/bold green]\n")
            # Pre-cargar mensajes previos en el thread de LangGraph (inyectar como historial)
            if datos_sesion and datos_sesion.get("mensajes"):
                historial_lc = mensajes_a_langchain(datos_sesion["mensajes"])
                try:
                    # Inyectar historial al grafo para restaurar contexto
                    _cfg_restore = {"configurable": {"thread_id": thread_id}}
                    for role, content in historial_lc:
                        agent_executor.update_state(_cfg_restore, {"messages": [(role, content)]})
                    console.print(f"[dim]Historial de {len(historial_lc)} mensajes restaurado en la memoria del agente.[/dim]\n")
                except Exception:
                    pass  # update_state puede no estar disponible; el hilo nuevo es suficiente

        elif opcion_sesion == "3":
            console.print()
            tabla = "[bold cyan]Sesiones guardadas:[/bold cyan]\n"
            for i, s in enumerate(sesiones_previas, 1):
                ts = s["ultima_actualizacion"][:16].replace("T", " ")
                tabla += f"  {i}. [bold]{s['thread_id']}[/bold] — {s['num_mensajes']} mensajes — {ts}\n"
            console.print(Panel(tabla, border_style="cyan"))
            try:
                idx_str = console.input("[bold yellow]> Ingresa el número de sesión a continuar (o ENTER para nueva): [/bold yellow]").strip()
                if idx_str.isdigit() and 1 <= int(idx_str) <= len(sesiones_previas):
                    thread_id = sesiones_previas[int(idx_str) - 1]["thread_id"]
                    console.print(f"[bold green]✓ Sesión '{thread_id}' seleccionada.[/bold green]\n")
            except (KeyboardInterrupt, EOFError):
                pass

    if not thread_id:
        import uuid
        thread_id = f"sesion_{uuid.uuid4().hex[:8]}"
        console.print(f"[bold green]✓ Nueva sesión iniciada: '{thread_id}'.[/bold green]\n")

    # Identificador de sesión para el hilo de memoria conversacional
    session_config = {"configurable": {"thread_id": thread_id}}

    def ejecutar_bateria_pruebas(config):
        console.print()
        console.rule("[bold cyan]Ejecución de Pruebas Automatizadas (RAG + Finanzas + Persistencia)[/bold cyan]")
        console.print()

        # TEST 1: CONSULTA DE REQUERIMIENTOS CON RAG
        query_req = "¿Cuáles son los requerimientos funcionales aprobados y en qué documento se basan?"
        res_req = invocar_agente_seguro({"messages": [("user", query_req)]}, config=config)
        resp_req_text = res_req["messages"][-1].content
        console.print(Panel(Markdown(resp_req_text), title="TEST 1 — Consulta RAG", border_style="cyan"))
        console.print()

        # TEST 2: EVALUACIÓN FINANCIERA AUTOMATIZADA CON TOOL CALLING
        query_fin = "Revisa los documentos del proyecto, busca los datos de inversión y evalúa si es viable financieramente."
        res_fin = invocar_agente_seguro({"messages": [("user", query_fin)]}, config=config)
        resp_fin_text = res_fin["messages"][-1].content
        console.print(Panel(Markdown(resp_fin_text), title="TEST 2 — Evaluación Financiera", border_style="green"))
        console.print()

        # TEST 3: COMPROBACIÓN DE MEMORIA Y HERRAMIENTA DE ESCRITURA
        query_write = "Tomando en cuenta la viabilidad que acabas de calcular en la consulta anterior, redacta un dictamen formal y guárdalo en un archivo llamado 'dictamen_kickoff.md'."
        res_write = invocar_agente_seguro({"messages": [("user", query_write)]}, config=config)
        resp_write_text = res_write["messages"][-1].content
        console.print(Panel(Markdown(resp_write_text), title="TEST 3 — Memoria y Escritura en Disco", border_style="magenta"))
        console.print()

    # ==============================================================================
    # GESTIÓN E INGESTA DINÁMICA DE DOCUMENTO
    # ==============================================================================
    console.print("[bold cyan]📄 Ingesta de Documentación del Proyecto[/bold cyan]")
    
    # Verificar si se pasó una ruta de archivo como argumento (ej. python src/kickoff_agent.py mi_doc.pdf)
    args_archivo = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    ruta_ingresada = args_archivo[0] if args_archivo else ""

    if not ruta_ingresada:
        console.print("Ingresa la ruta de un documento ([bold].pdf, .txt, .md[/bold]) para hacerle preguntas,")
        console.print("o presiona [bold green]ENTER[/bold green] para cargar automáticamente los archivos de la carpeta [bold]docs/[/bold].")
        try:
            ruta_ingresada = console.input("[bold yellow]> Ruta del documento (o ENTER para usar docs/): [/bold yellow]").strip().strip('"').strip("'")
        except (KeyboardInterrupt, EOFError):
            ruta_ingresada = ""

    if ruta_ingresada:
        p_ingresada = Path(ruta_ingresada)
        if not p_ingresada.is_absolute():
            p_ingresada = BASE_DIR / ruta_ingresada
        if p_ingresada.exists():
            with console.status(f"[bold cyan]Indexando documento '{p_ingresada.name}' en ChromaDB...[/bold cyan]"):
                chunks_cargados = agregar_documento_al_agente(p_ingresada)
            console.print(f"[bold green]✓ Documento '{p_ingresada.name}' indexado exitosamente ({chunks_cargados} fragmentos añadidos a la base de conocimiento).[/bold green]\n")
        else:
            console.print(f"[yellow]⚠ No se encontró el archivo '{ruta_ingresada}'. Se utilizará la base de conocimiento predeterminada.[/yellow]\n")
    else:
        # Cargar archivos de docs/ automáticamente
        archivos_en_docs = [f for f in DOCS_DIR.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".txt", ".md", ".markdown", ".csv", ".json"]]
        if archivos_en_docs:
            with console.status("[bold cyan]Indexando documentos de la carpeta docs/...[/bold cyan]"):
                total_chunks = 0
                for f in archivos_en_docs:
                    total_chunks += agregar_documento_al_agente(f)
            nombres = ", ".join(f.name for f in archivos_en_docs)
            console.print(f"[bold green]✓ Documentos indexados desde docs/: {nombres} ({total_chunks} fragmentos listos).[/bold green]\n")
        else:
            console.print("[bold green]✓ Base de conocimiento predeterminada activa (Actas y Especificaciones IEEE 830).[/bold green]\n")

    # ==============================================================================
    # MODO INTERACTIVO (PREGUNTAS Y RESPUESTAS CON GROQ RAG)
    # ==============================================================================
    console.rule("[bold cyan]Modo Preguntas y Respuestas (RAG + Inferencia Groq)[/bold cyan]")
    console.print()
    
    docs_activos = ", ".join(f"[bold]{d}[/bold]" for d in DOCUMENTOS_REGISTRADOS)
    panel_info = (
        f"📚 [bold cyan]Documentos activos:[/bold cyan] {docs_activos}\n\n"
        "💡 [bold]Puedes consultar:[/bold]\n"
        "  • '¿De qué trata este documento y cuáles son sus objetivos?'\n"
        "  • '¿Cuáles son los requerimientos funcionales y no funcionales?'\n"
        "  • '¿Cuál es el presupuesto o inversión inicial y es viable financieramente?'\n"
        "  • '¿Quiénes son los autores o participantes?'\n\n"
        "⚡ [bold]Comandos disponibles:[/bold]\n"
        "  • [yellow]/cargar <ruta>[/yellow]   : Cargar e indexar otro documento en caliente\n"
        "  • [yellow]/documentos[/yellow]      : Ver lista de documentos cargados\n"
        "  • [yellow]/limpiar[/yellow]         : Reiniciar la memoria de la conversación\n"
        "  • [yellow]/historial[/yellow]       : Ver historial de la sesión actual\n"
        "  • [yellow]/exportar[/yellow]        : Exportar resumen de la sesión a archivo\n"
        "  • [yellow]/sesiones[/yellow]        : Ver y gestionar sesiones guardadas\n"
        "  • [yellow]/test[/yellow]            : Ejecutar la batería de pruebas automatizadas\n"
        "  • [yellow]/ayuda[/yellow]           : Ver este menú de ayuda\n"
        "  • [yellow]salir[/yellow]            : Guardar y finalizar la sesión"
    )
    console.print(Panel(panel_info, title="KickoffAgent Q&A", border_style="cyan"))
    console.print()

    thread_id_interactivo = thread_id
    interactive_config = {"configurable": {"thread_id": thread_id_interactivo}}
    # Lista local de mensajes para persistencia al final de sesión
    historial_sesion: list = []

    while True:
        try:
            query = console.input("[bold yellow]> Pregunta sobre el documento:[/bold yellow] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Sesión cerrada.[/cyan]")
            break

        clean_query = query.strip()
        if not clean_query:
            continue

        if clean_query.lower() in ["salir", "exit", "/salir", "/exit"]:
            # Guardar sesión antes de salir
            guardar_sesion(
                thread_id_interactivo,
                historial_sesion,
                metadata={"documentos": DOCUMENTOS_REGISTRADOS}
            )
            console.print(f"[bold green]✓ Sesión '{thread_id_interactivo}' guardada. ¡Hasta luego![/bold green]")
            break

        if clean_query.lower() in ["/ayuda", "/help"]:
            console.print(Panel(panel_info, title="Ayuda KickoffAgent", border_style="cyan"))
            continue

        if clean_query.lower() in ["/documentos", "/docs"]:
            lista_docs = "\n".join(f"- {d}" for d in DOCUMENTOS_REGISTRADOS)
            console.print(Panel(f"Documentos cargados actualmente:\n\n{lista_docs}", title="Base de Conocimiento", border_style="cyan"))
            continue

        if clean_query.lower() in ["/historial", "/historia"]:
            if not historial_sesion:
                console.print("[yellow]No hay mensajes en el historial de esta sesión aún.[/yellow]\n")
            else:
                texto_hist = ""
                for m in historial_sesion:
                    emoji = "🧑" if m["role"] == "user" else "🤖"
                    texto_hist += f"**{emoji} {m['role'].upper()}:** {m['content']}\n\n"
                console.print(Panel(Markdown(texto_hist), title=f"Historial — {len(historial_sesion)} mensajes", border_style="cyan"))
            continue

        if clean_query.lower() in ["/exportar", "/export"]:
            if not historial_sesion:
                console.print("[yellow]No hay mensajes para exportar en esta sesión.[/yellow]\n")
            else:
                import datetime
                contenido = ""
                for m in historial_sesion:
                    emoji = "🧑" if m["role"] == "user" else "🤖"
                    contenido += f"**{emoji} {m['role'].upper()}:** {m['content']}\n\n---\n\n"
                nombre_export = f"sesion_{thread_id_interactivo}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.md"
                from pathlib import Path as _Path
                out = BASE_DIR / "output" / nombre_export
                out.write_text(
                    f"# Historial de Sesión — KickoffAgent\n_Thread: {thread_id_interactivo}_\n\n---\n\n" + contenido,
                    encoding="utf-8"
                )
                console.print(f"[bold green]✓ Sesión exportada a: output/{nombre_export}[/bold green]\n")
            continue

        if clean_query.lower() in ["/sesiones"]:
            todas = listar_sesiones()
            if not todas:
                console.print("[yellow]No hay sesiones guardadas.[/yellow]\n")
            else:
                tabla = ""
                for i, s in enumerate(todas, 1):
                    ts = s["ultima_actualizacion"][:16].replace("T", " ")
                    tabla += f"  {i}. [bold]{s['thread_id']}[/bold] — {s['num_mensajes']} msgs — {ts}\n"
                console.print(Panel(tabla, title="Sesiones guardadas", border_style="cyan"))
                try:
                    acc = console.input("[dim]Ingresa 'del N' para eliminar o ENTER para cerrar: [/dim]").strip()
                    if acc.lower().startswith("del "):
                        idx_del = acc.split()[1]
                        if idx_del.isdigit() and 1 <= int(idx_del) <= len(todas):
                            tid_del = todas[int(idx_del) - 1]["thread_id"]
                            eliminar_sesion(tid_del)
                            console.print(f"[bold green]✓ Sesión '{tid_del}' eliminada.[/bold green]")
                except (KeyboardInterrupt, EOFError):
                    pass
            continue

        if clean_query.lower().startswith("/cargar ") or clean_query.lower().startswith("/doc "):
            partes = clean_query.split(maxsplit=1)
            if len(partes) > 1:
                ruta_nueva = partes[1].strip().strip('"').strip("'")
                p_nueva = Path(ruta_nueva)
                if not p_nueva.is_absolute():
                    p_nueva = BASE_DIR / ruta_nueva
                if p_nueva.exists():
                    with console.status(f"[bold cyan]Indexando '{p_nueva.name}'...[/bold cyan]"):
                        c = agregar_documento_al_agente(p_nueva)
                    console.print(f"[bold green]✓ Documento '{p_nueva.name}' indexado ({c} nuevos fragmentos). Ya puedes hacerle preguntas.[/bold green]\n")
                else:
                    console.print(f"[bold red]✗ El archivo '{ruta_nueva}' no fue encontrado.[/bold red]\n")
            else:
                console.print("[yellow]Uso: /cargar <ruta_al_archivo_pdf_o_txt>[/yellow]\n")
            continue

        if clean_query.lower() == "/limpiar":
            import uuid
            thread_id_interactivo = f"sesion_{uuid.uuid4().hex[:8]}"
            interactive_config = {"configurable": {"thread_id": thread_id_interactivo}}
            historial_sesion = []
            console.print("[bold green]✓ Memoria conversacional reiniciada. Puedes comenzar un nuevo tema.[/bold green]\n")
            continue

        if clean_query.lower() == "/test":
            ejecutar_bateria_pruebas(interactive_config)
            continue

        try:
            with console.status("[bold cyan]Consultando con Groq y analizando documento...[/bold cyan]"):
                res = invocar_agente_seguro({"messages": [("user", clean_query)]}, config=interactive_config)
            respuesta = res["messages"][-1].content
            # Persistir turno en historial local
            historial_sesion.append({"role": "user", "content": clean_query})
            historial_sesion.append({"role": "ai", "content": respuesta})
            # Auto-guardar sesión en disco
            guardar_sesion(
                thread_id_interactivo,
                historial_sesion,
                metadata={"documentos": DOCUMENTOS_REGISTRADOS}
            )
            console.print()
            console.print(Panel(Markdown(respuesta), title="KickoffAgent (Groq)", border_style="cyan"))
            console.print()
        except Exception as e:
            console.print(f"[red]Error al procesar la consulta: {e}[/red]")
