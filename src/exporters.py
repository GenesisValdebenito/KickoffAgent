"""Módulo de Exportación Formal de Informes (Word .docx y PDF).
Convierte informes y especificaciones en Markdown generadas por KickoffAgent
en documentos ejecutivos corporativos con estilos, tablas y metadatos profesionales.
"""

from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Any

# ------------------------------------------------------------------------------
# 1. PARSER AUXILIAR DE CONTENIDO MARKDOWN
# ------------------------------------------------------------------------------

def limpiar_formato_inline(texto: str) -> str:
    """Elimina sintaxis Markdown común para texto plano."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"\*(.+?)\*", r"\1", texto)
    texto = re.sub(r"`(.+?)`", r"\1", texto)
    return texto.strip()


def parsear_lineas_markdown(contenido_md: str) -> List[Dict[str, Any]]:
    """Parsea el Markdown en bloques estructurados:
    - encabezados (h1, h2, h3)
    - tablas (bloques de líneas con '|')
    - listas con viñetas
    - párrafos regulares
    """
    lineas = contenido_md.splitlines()
    bloques: List[Dict[str, Any]] = []
    buffer_tabla: List[str] = []

    def flush_tabla():
        if buffer_tabla:
            tabla_datos = parsear_tabla_markdown(buffer_tabla)
            if tabla_datos:
                bloques.append({"tipo": "tabla", "datos": tabla_datos})
            buffer_tabla.clear()

    for linea in lineas:
        linea_strip = linea.strip()

        # Detección de fila de tabla
        if linea_strip.startswith("|") and linea_strip.endswith("|"):
            buffer_tabla.append(linea_strip)
            continue
        else:
            flush_tabla()

        if not linea_strip:
            continue

        if linea_strip.startswith("### "):
            bloques.append({"tipo": "h3", "texto": linea_strip[4:].strip()})
        elif linea_strip.startswith("## "):
            bloques.append({"tipo": "h2", "texto": linea_strip[3:].strip()})
        elif linea_strip.startswith("# "):
            bloques.append({"tipo": "h1", "texto": linea_strip[2:].strip()})
        elif linea_strip.startswith(("- ", "* ", "+ ")):
            bloques.append({"tipo": "viñeta", "texto": linea_strip[2:].strip()})
        elif re.match(r"^\d+\.\s+", linea_strip):
            texto_num = re.sub(r"^\d+\.\s+", "", linea_strip)
            bloques.append({"tipo": "enumerado", "texto": texto_num})
        else:
            bloques.append({"tipo": "parrafo", "texto": linea_strip})

    flush_tabla()
    return bloques


def parsear_tabla_markdown(filas_raw: List[str]) -> List[List[str]]:
    """Extrae las celdas de una tabla Markdown, ignorando la línea de separación."""
    datos: List[List[str]] = []
    for fila in filas_raw:
        # Ignorar fila separadora (| :--- | :--- |)
        if re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", fila):
            continue
        celdas = [c.strip() for c in fila.strip("|").split("|")]
        if any(celdas):
            datos.append(celdas)
    return datos


# ------------------------------------------------------------------------------
# 2. EXPORTADOR A WORD (.DOCX)
# ------------------------------------------------------------------------------

def exportar_a_docx(contenido_md: str, ruta_salida: Path, titulo_doc: Optional[str] = None) -> Path:
    """Genera un documento Word corporativo (.docx) a partir del contenido Markdown."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except ImportError as e:
        raise ImportError(
            "La librería 'python-docx' es requerida para exportar a Word. "
            "Instálala con: pip install python-docx"
        ) from e

    doc = Document()

    # Configuración de márgenes a 2 cm (aprox 0.8 pulgadas)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Colores corporativos
    NAVY_HEX = "1A365D"
    NAVY = RGBColor(26, 54, 93)
    SLATE = RGBColor(74, 85, 104)
    TEXT_COLOR = RGBColor(45, 55, 72)

    # Encabezado corporativo
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run_hdr = p_header.add_run("KICKOFFAGENT | EVALUACIÓN ESTRATÉGICA TI")
    run_hdr.font.size = Pt(8.5)
    run_hdr.font.bold = True
    run_hdr.font.color.rgb = SLATE

    # Título principal del documento
    titulo_final = titulo_doc or "Dictamen Formal de Kickoff de Proyecto"
    bloques = parsear_lineas_markdown(contenido_md)

    # Si el primer bloque es H1, usarlo como título
    if bloques and bloques[0]["tipo"] == "h1":
        titulo_final = limpiar_formato_inline(bloques[0]["texto"])
        bloques = bloques[1:]

    p_title = doc.add_paragraph()
    run_title = p_title.add_run(titulo_final)
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY
    p_title.paragraph_format.space_after = Pt(4)

    # Subtítulo con metadatos
    p_sub = doc.add_paragraph()
    fecha_hoy = datetime.now().strftime("%d-%m-%Y %H:%M")
    run_sub = p_sub.add_run(f"Emitido por KickoffAgent • Fecha: {fecha_hoy} • Estado: Formalizado")
    run_sub.font.size = Pt(9.5)
    run_sub.font.italic = True
    run_sub.font.color.rgb = SLATE
    p_sub.paragraph_format.space_after = Pt(16)

    def set_cell_background(cell, hex_color: str):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), hex_color)
        tcPr.append(shd)

    def agregar_texto_con_negrita(parrafo, texto: str):
        # Separa fragmentos en negrita **texto**
        partes = re.split(r"(\*\*.+?\*\*)", texto)
        for parte in partes:
            if parte.startswith("**") and parte.endswith("**"):
                r = parrafo.add_run(parte[2:-2])
                r.bold = True
            else:
                parrafo.add_run(parte)

    # Renderizar bloques
    for bloque in bloques:
        tipo = bloque["tipo"]

        if tipo == "h1":
            p = doc.add_paragraph()
            r = p.add_run(limpiar_formato_inline(bloque["texto"]))
            r.font.size = Pt(16)
            r.font.bold = True
            r.font.color.rgb = NAVY
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)

        elif tipo == "h2":
            p = doc.add_paragraph()
            r = p.add_run(limpiar_formato_inline(bloque["texto"]))
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = NAVY
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(3)

        elif tipo == "h3":
            p = doc.add_paragraph()
            r = p.add_run(limpiar_formato_inline(bloque["texto"]))
            r.font.size = Pt(11)
            r.font.bold = True
            r.font.color.rgb = SLATE
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)

        elif tipo == "viñeta":
            p = doc.add_paragraph(style="List Bullet")
            agregar_texto_con_negrita(p, bloque["texto"])
            p.paragraph_format.space_after = Pt(2)

        elif tipo == "enumerado":
            p = doc.add_paragraph(style="List Number")
            agregar_texto_con_negrita(p, bloque["texto"])
            p.paragraph_format.space_after = Pt(2)

        elif tipo == "parrafo":
            p = doc.add_paragraph()
            agregar_texto_con_negrita(p, bloque["texto"])
            p.paragraph_format.space_after = Pt(6)

        elif tipo == "tabla":
            datos_tabla = bloque["datos"]
            if not datos_tabla or len(datos_tabla) < 1:
                continue

            num_cols = max(len(fila) for fila in datos_tabla)
            num_filas = len(datos_tabla)

            table = doc.add_table(rows=num_filas, cols=num_cols)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True

            for row_idx, fila in enumerate(datos_tabla):
                is_header = (row_idx == 0)
                for col_idx in range(num_cols):
                    cell = table.cell(row_idx, col_idx)
                    val = fila[col_idx] if col_idx < len(fila) else ""
                    val_limpio = limpiar_formato_inline(val)

                    p_cell = cell.paragraphs[0]
                    p_cell.text = ""
                    p_cell.paragraph_format.space_before = Pt(2)
                    p_cell.paragraph_format.space_after = Pt(2)

                    if is_header:
                        set_cell_background(cell, NAVY_HEX)
                        run_cell = p_cell.add_run(val_limpio)
                        run_cell.bold = True
                        run_cell.font.color.rgb = RGBColor(255, 255, 255)
                        run_cell.font.size = Pt(9.5)
                    else:
                        # Color alterno en filas
                        if row_idx % 2 == 1:
                            set_cell_background(cell, "F7FAFC")
                        run_cell = p_cell.add_run(val_limpio)
                        run_cell.font.size = Pt(9)
                        run_cell.font.color.rgb = TEXT_COLOR
                        if "**" in val:
                            run_cell.bold = True

            p_space = doc.add_paragraph()
            p_space.paragraph_format.space_after = Pt(8)

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(ruta_salida))
    return ruta_salida


# ------------------------------------------------------------------------------
# 3. EXPORTADOR A PDF (REPORTLAB)
# ------------------------------------------------------------------------------

def exportar_a_pdf(contenido_md: str, ruta_salida: Path, titulo_doc: Optional[str] = None) -> Path:
    """Genera un documento PDF corporativo a partir del contenido Markdown usando ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.pdfgen import canvas
    except ImportError as e:
        raise ImportError(
            "La librería 'reportlab' es requerida para exportar a PDF. "
            "Instálala con: pip install reportlab"
        ) from e

    class NumberedCanvas(canvas.Canvas):
        """Canvas con numeración de página dinámica: 'Página X de Y'."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_number(num_pages)
                super().showPage()
            super().save()

        def draw_page_number(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))

            # Encabezado
            self.drawString(54, 750, "KICKOFFAGENT | EVALUACIÓN ESTRATÉGICA TI")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

            # Pie de página
            self.line(54, 45, 558, 45)
            texto_pie = f"Página {self._pageNumber} de {page_count}"
            self.drawRightString(558, 32, texto_pie)
            self.drawString(54, 32, "Confidencial - Dictamen emitido por KickoffAgent")
            self.restoreState()

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(ruta_salida),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=64,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Estilos corporativos personalizados
    NAVY = colors.HexColor("#1A365D")
    SLATE = colors.HexColor("#4A5568")
    LIGHT_BG = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#CBD5E0")

    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=NAVY,
        spaceAfter=4
    )

    style_sub = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=SLATE,
        spaceAfter=12
    )

    style_h1 = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=4
    )

    style_h2 = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=NAVY,
        spaceBefore=8,
        spaceAfter=3
    )

    style_h3 = ParagraphStyle(
        "Heading3_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=SLATE,
        spaceBefore=6,
        spaceAfter=2
    )

    style_body = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=5
    )

    style_bullet = ParagraphStyle(
        "Bullet_Custom",
        parent=style_body,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )

    style_cell_header = ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    style_cell_body = ParagraphStyle(
        "CellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#2D3748")
    )

    def convertir_a_html_reportlab(texto: str) -> str:
        """Convierte markdown básico (**bold**, *italic*) a etiquetas HTML de ReportLab."""
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
        t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
        t = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", t)
        return t

    story = []

    bloques = parsear_lineas_markdown(contenido_md)

    # Título principal
    titulo_final = titulo_doc or "Dictamen Formal de Kickoff de Proyecto"
    if bloques and bloques[0]["tipo"] == "h1":
        titulo_final = limpiar_formato_inline(bloques[0]["texto"])
        bloques = bloques[1:]

    story.append(Paragraph(titulo_final, style_title))
    fecha_hoy = datetime.now().strftime("%d-%m-%Y %H:%M")
    story.append(Paragraph(f"Emitido por KickoffAgent • Fecha: {fecha_hoy} • Estado: Formalizado", style_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=10))

    for bloque in bloques:
        tipo = bloque["tipo"]
        texto = bloque.get("texto", "")

        if tipo == "h1":
            story.append(Paragraph(limpiar_formato_inline(texto), style_h1))
        elif tipo == "h2":
            story.append(Paragraph(limpiar_formato_inline(texto), style_h2))
        elif tipo == "h3":
            story.append(Paragraph(limpiar_formato_inline(texto), style_h3))
        elif tipo == "viñeta":
            html_txt = "• " + convertir_a_html_reportlab(texto)
            story.append(Paragraph(html_txt, style_bullet))
        elif tipo == "enumerado":
            html_txt = "1. " + convertir_a_html_reportlab(texto)
            story.append(Paragraph(html_txt, style_bullet))
        elif tipo == "parrafo":
            story.append(Paragraph(convertir_a_html_reportlab(texto), style_body))
        elif tipo == "tabla":
            datos_tabla = bloque["datos"]
            if not datos_tabla:
                continue

            # Convertir celdas en Flowables Paragraph para permitir salto de línea
            filas_flowables = []
            for r_idx, fila in enumerate(datos_tabla):
                fila_flow = []
                is_header = (r_idx == 0)
                st = style_cell_header if is_header else style_cell_body
                for celda in fila:
                    celda_html = convertir_a_html_reportlab(celda)
                    fila_flow.append(Paragraph(celda_html, st))
                filas_flowables.append(fila_flow)

            # Ancho disponible: 504 pt (letter width 612 - 108 margins)
            ancho_total = 504
            num_cols = max(len(f) for f in datos_tabla)
            col_widths = [ancho_total / num_cols] * num_cols

            t = Table(filas_flowables, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 8))

    doc.build(story, canvasmaker=NumberedCanvas)
    return ruta_salida


# ------------------------------------------------------------------------------
# 4. ORQUESTADOR PRINCIPAL DE EXPORTACIÓN
# ------------------------------------------------------------------------------

def exportar_informe_multiformato(
    contenido_markdown: str,
    nombre_base: str,
    directorio_salida: Path,
    formato: str = "todos"
) -> Dict[str, str]:
    """Exporta el contenido a uno o múltiples formatos (.md, .docx, .pdf).

    Args:
        contenido_markdown: Texto del informe en formato Markdown.
        nombre_base: Nombre base para los archivos (sin extensión o con ella).
        directorio_salida: Directorio destino (Path).
        formato: 'docx', 'pdf', 'md' o 'todos'.

    Returns:
        Diccionario con las rutas absolutas de los archivos generados y errores si los hubo.
    """
    clean_stem = Path(nombre_base).stem or "dictamen_kickoff"
    directorio_salida.mkdir(parents=True, exist_ok=True)

    fmt = formato.strip().lower()
    generar_md = fmt in ("md", "markdown", "todos", "all")
    generar_docx = fmt in ("docx", "word", "todos", "all")
    generar_pdf = fmt in ("pdf", "todos", "all")

    archivos_creados: Dict[str, str] = {}
    errores: List[str] = []

    # 1. Guardar Markdown siempre como respaldo o si se solicita
    if generar_md:
        ruta_md = directorio_salida / f"{clean_stem}.md"
        try:
            ruta_md.write_text(contenido_markdown, encoding="utf-8")
            archivos_creados["md"] = str(ruta_md)
        except Exception as e:
            errores.append(f"Error al generar Markdown: {str(e)}")

    # 2. Generar Word (.docx)
    if generar_docx:
        ruta_docx = directorio_salida / f"{clean_stem}.docx"
        try:
            exportar_a_docx(contenido_markdown, ruta_docx)
            archivos_creados["docx"] = str(ruta_docx)
        except Exception as e:
            errores.append(f"Word (.docx) no generado: {str(e)}")

    # 3. Generar PDF (.pdf)
    if generar_pdf:
        ruta_pdf = directorio_salida / f"{clean_stem}.pdf"
        try:
            exportar_a_pdf(contenido_markdown, ruta_pdf)
            archivos_creados["pdf"] = str(ruta_pdf)
        except Exception as e:
            errores.append(f"PDF (.pdf) no generado: {str(e)}")

    return {
        "archivos": archivos_creados,
        "errores": errores
    }
