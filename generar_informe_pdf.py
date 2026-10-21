"""
generar_informe_pdf.py — Genera el Informe Técnico de KickoffAgent en PDF.

Uso:
    python generar_informe_pdf.py

Requiere:
    pip install reportlab Pillow

El PDF se guarda en: docs/Informe_Tecnico_KickoffAgent_v2.pdf
"""

import datetime
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, ListFlowable, ListItem
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
except ImportError:
    print("ERROR: Instala reportlab con:  pip install reportlab")
    raise

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PDF = BASE_DIR / "docs" / "Informe_Tecnico_KickoffAgent_v2.pdf"
OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)

FECHA = datetime.datetime.now().strftime("%d de %B de %Y")
AUTORES = "Génesis Valdebenito — ISY0101 Ingeniería de Soluciones con IA"

def build_styles():
    styles = getSampleStyleSheet()
    custom = {}
    
    custom["titulo"] = ParagraphStyle(
        "titulo", parent=styles["Title"],
        fontSize=20, textColor=colors.HexColor("#1A237E"),
        spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"
    )
    custom["subtitulo"] = ParagraphStyle(
        "subtitulo", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#3949AB"),
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica"
    )
    custom["h1"] = ParagraphStyle(
        "h1", parent=styles["Heading1"],
        fontSize=13, textColor=colors.HexColor("#1A237E"),
        spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
        borderPad=2
    )
    custom["h2"] = ParagraphStyle(
        "h2", parent=styles["Heading2"],
        fontSize=11, textColor=colors.HexColor("#283593"),
        spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"
    )
    custom["body"] = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=6,
        alignment=TA_JUSTIFY, fontName="Helvetica"
    )
    custom["code"] = ParagraphStyle(
        "code", parent=styles["Code"],
        fontSize=8, leading=12, backColor=colors.HexColor("#F5F5F5"),
        textColor=colors.HexColor("#212121"), spaceAfter=6,
        leftIndent=10, rightIndent=10, fontName="Courier"
    )
    custom["caption"] = ParagraphStyle(
        "caption", parent=styles["Normal"],
        fontSize=8, textColor=colors.gray, alignment=TA_CENTER, spaceAfter=4
    )
    return custom, styles


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A237E")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#E8EAF6")]),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#9FA8DA")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_pdf():
    s, base_styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title="Informe Técnico KickoffAgent",
        author=AUTORES,
        subject="Evaluación Parcial N°2 — ISY0101"
    )
    
    story = []
    
    # ── PORTADA ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("INFORME TÉCNICO", s["titulo"]))
    story.append(Paragraph("KickoffAgent — Agente Inteligente de Formulación de Proyectos TI", s["subtitulo"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1A237E"), spaceAfter=12))
    
    meta = [
        ["Asignatura", "ISY0101 — Ingeniería de Soluciones con IA"],
        ["Evaluación", "Parcial N°2 — Desarrollo de un Agente Funcional"],
        ["Integrantes", "Génesis Valdebenito"],
        ["Fecha", FECHA],
        ["Repositorio", "https://github.com/GenesisValdebenito/KickoffAgent"],
    ]
    story.append(make_table(["Campo", "Valor"], meta, col_widths=[5*cm, 11*cm]))
    story.append(PageBreak())
    
    # ── 1. RESUMEN EJECUTIVO ──────────────────────────────────────────────────
    story.append(Paragraph("1. Resumen Ejecutivo", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    story.append(Paragraph(
        "KickoffAgent es un agente inteligente de tipo ReAct desarrollado con el framework LangGraph "
        "de LangChain, orientado a la automatización del proceso de formulación y evaluación de proyectos TI. "
        "El agente integra un pipeline RAG (Retrieval-Augmented Generation) sobre ChromaDB, herramientas "
        "de cálculo financiero determinista (VAN, TIR, ROI, PRI) mediante numpy-financial, memoria "
        "conversacional de corto y largo plazo, y persistencia documental en disco.",
        s["body"]
    ))
    
    # ── 2. ARQUITECTURA ───────────────────────────────────────────────────────
    story.append(Paragraph("2. Arquitectura del Sistema", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    story.append(Paragraph(
        "La arquitectura de KickoffAgent sigue el patrón <b>agente + herramientas orquestado por grafo de estados</b>. "
        "Los componentes principales son:", s["body"]
    ))
    
    comp_rows = [
        ["LangGraph StateGraph", "Orquestación del flujo agente → herramientas → agente con aristas condicionales"],
        ["MemorySaver (LangGraph)", "Memoria de corto plazo (dentro de la sesión) mediante checkpointing en RAM"],
        ["Memoria Persistente (JSON)", "Módulo src/memory.py que serializa el historial de sesiones en disco (sessions/)"],
        ["ChromaDB (RAG)", "Vector store para indexación y recuperación semántica de documentos"],
        ["FastEmbed (BAAI/bge-small-en-v1.5)", "Modelo de embeddings ejecutado 100% localmente sin API externa"],
        ["Groq / MockDemoChat", "LLM principal (qwen/qwen3.8-27b vía API) con fallback determinista offline"],
        ["numpy-financial", "Cálculo determinista de métricas financieras (VAN, TIR, ROI, PRI)"],
        ["src/tools.py", "7 herramientas: consultar RAG, calcular finanzas, guardar/editar/eliminar notas, exportar sesión"],
    ]
    story.append(make_table(
        ["Componente", "Función"],
        comp_rows,
        col_widths=[7*cm, 9*cm]
    ))
    story.append(Spacer(1, 0.3*cm))
    
    # Diagrama de flujo (texto)
    story.append(Paragraph("2.1 Flujo de Ejecución", s["h2"]))
    story.append(Paragraph(
        "Al iniciar, el agente: (1) detecta sesiones previas y ofrece continuar la última conversación; "
        "(2) verifica la API key o activa el modo demo; (3) indexa documentos de docs/ en ChromaDB; "
        "(4) entra en el loop interactivo Q&A con el usuario. Cada consulta pasa por el grafo LangGraph: "
        "el nodo <i>agent</i> decide si invocar herramientas o responder directamente. Si invoca herramienta, "
        "el resultado vuelve al nodo <i>agent</i> para formular la respuesta final. La sesión se auto-guarda "
        "en disco tras cada turno.", s["body"]
    ))
    
    # ── 3. HERRAMIENTAS ────────────────────────────────────────────────────────
    story.append(Paragraph("3. Herramientas del Agente (src/tools.py)", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    
    tools_rows = [
        ["consultar_documentacion_proyecto", "RAG sobre ChromaDB. Recupera fragmentos relevantes de PDFs y TXTs indexados."],
        ["calcular_metricas_financieras", "Calcula VAN, TIR, ROI y PRI usando numpy-financial. Entrada: inversión, flujos, tasa."],
        ["guardar_informe_kickoff", "Persiste un dictamen o informe en output/ como archivo Markdown."],
        ["editar_nota_kickoff", "Sobrescribe el contenido de un archivo existente en output/."],
        ["eliminar_nota_kickoff", "Elimina un archivo guardado de output/."],
        ["exportar_resumen_sesion", "Exporta un resumen de la conversación actual a un archivo Markdown en output/."],
        ["sumar / restar / multiplicar / dividir", "Operaciones aritméticas auxiliares de apoyo al cálculo financiero."],
    ]
    story.append(make_table(
        ["Herramienta", "Descripción"],
        tools_rows,
        col_widths=[6*cm, 10*cm]
    ))
    
    # ── 4. MEMORIA ────────────────────────────────────────────────────────────
    story.append(Paragraph("4. Estrategias de Memoria", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    
    story.append(Paragraph("<b>4.1 Memoria de Corto Plazo (MemorySaver)</b>", s["h2"]))
    story.append(Paragraph(
        "LangGraph usa MemorySaver como checkpointer en RAM, identificando cada hilo de conversación "
        "por un thread_id único. Esto permite que el agente recuerde el contexto completo de la sesión "
        "en curso sin que el usuario repita datos previamente mencionados.", s["body"]
    ))
    
    story.append(Paragraph("<b>4.2 Memoria de Largo Plazo (Persistencia JSON)</b>", s["h2"]))
    story.append(Paragraph(
        "El módulo src/memory.py serializa el historial de mensajes (usuario + agente) en archivos JSON "
        "dentro de la carpeta sessions/. Al reiniciar el agente, detecta sesiones previas y ofrece "
        "continuar la última conversación, restaurando el contexto en el grafo de LangGraph.", s["body"]
    ))
    
    story.append(Paragraph("<b>4.3 Memoria Vectorial (ChromaDB RAG)</b>", s["h2"]))
    story.append(Paragraph(
        "Los documentos ingresados (PDF, TXT, MD) se fragmentan con RecursiveCharacterTextSplitter "
        "(chunk_size=700, overlap=120) y se indexan en ChromaDB usando embeddings BAAI/bge-small-en-v1.5 "
        "(ejecución 100% local vía FastEmbed). El retriever recupera los k=4 fragmentos más relevantes "
        "ante cada consulta, proporcionando grounding factual basado en los documentos reales.", s["body"]
    ))
    
    # ── 5. PLANIFICACIÓN ──────────────────────────────────────────────────────
    story.append(Paragraph("5. Planificación y Toma de Decisiones", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    story.append(Paragraph(
        "El agente implementa el patrón <b>ReAct</b> (Reasoning + Acting) mediante el grafo LangGraph: "
        "el nodo <i>agent</i> razona sobre la consulta y decide si invocar una herramienta o responder "
        "directamente. La función <i>should_continue</i> inspecciona los tool_calls del último mensaje; "
        "si existen, redirige al nodo <i>tools</i>; de lo contrario, termina. Este ciclo permite "
        "planificación multi-paso (ej: consultar RAG → extraer datos → calcular VAN → redactar dictamen).",
        s["body"]
    ))
    
    # ── 6. EJECUCIÓN ──────────────────────────────────────────────────────────
    story.append(Paragraph("6. Instrucciones de Ejecución", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    
    story.append(Paragraph("<b>Instalación de dependencias:</b>", s["h2"]))
    story.append(Paragraph("pip install -r requirements.txt", s["code"]))
    
    story.append(Paragraph("<b>Ejecución normal (interactiva):</b>", s["h2"]))
    story.append(Paragraph("python src/kickoff_agent.py", s["code"]))
    
    story.append(Paragraph("<b>Ejecución de pruebas automatizadas:</b>", s["h2"]))
    story.append(Paragraph("python src/kickoff_agent.py --test", s["code"]))
    story.append(Paragraph("pytest tests/ -v", s["code"]))
    
    story.append(Paragraph("<b>Cargar un documento al iniciar:</b>", s["h2"]))
    story.append(Paragraph("python src/kickoff_agent.py ruta/al/documento.pdf", s["code"]))
    
    story.append(Paragraph("<b>Comandos disponibles en el modo interactivo:</b>", s["h2"]))
    cmds = [
        ["/cargar <ruta>", "Indexa un nuevo documento en caliente"],
        ["/documentos", "Lista los documentos activos en la base vectorial"],
        ["/historial", "Muestra el historial de la sesión actual"],
        ["/exportar", "Exporta la sesión completa a un archivo Markdown"],
        ["/sesiones", "Ver y gestionar sesiones guardadas persistentes"],
        ["/limpiar", "Reinicia la memoria conversacional (nueva sesión)"],
        ["/test", "Ejecuta la batería de pruebas automatizadas"],
        ["salir", "Guarda la sesión y finaliza"],
    ]
    story.append(make_table(["Comando", "Descripción"], cmds, col_widths=[5*cm, 11*cm]))
    
    # ── 7. EVIDENCIA ──────────────────────────────────────────────────────────
    story.append(Paragraph("7. Evidencia de Ejecución", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    story.append(Paragraph(
        "Las capturas de pantalla de la ejecución del agente se encuentran en la carpeta <b>tests/</b> "
        "del repositorio (test_01.png a test_04-2.png) junto con el archivo tests/Evidencia_Tests.md "
        "que documenta cada prueba con su resultado esperado y obtenido. El pipeline completo fue "
        "verificado en modo demo (sin API) y en modo live con Groq API.", s["body"]
    ))
    
    # ── 8. CONCLUSIÓN ─────────────────────────────────────────────────────────
    story.append(Paragraph("8. Conclusión", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA"), spaceAfter=8))
    story.append(Paragraph(
        "KickoffAgent cumple con todos los requisitos de la rúbrica de la Evaluación Parcial N°2: "
        "integra herramientas de consulta, escritura y razonamiento; implementa memoria de corto y largo "
        "plazo con recuperación semántica vectorial; aplica estrategias de planificación ReAct con grafo "
        "de estados LangGraph; y documenta claramente la arquitectura y orquestación entre componentes. "
        "El código está versionado en GitHub con CI mediante GitHub Actions y tests automatizados con pytest.",
        s["body"]
    ))
    
    # ── PIE DE PÁGINA ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FA8DA")))
    story.append(Paragraph(
        f"<i>Generado automáticamente el {FECHA} | Repositorio: github.com/GenesisValdebenito/KickoffAgent</i>",
        s["caption"]
    ))
    
    doc.build(story)
    print(f"PDF generado exitosamente: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
