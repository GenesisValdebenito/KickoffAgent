"""Módulo de Herramientas (Tools) del Agente KickoffAgent.
Define las herramientas de cálculo determinista, operaciones matemáticas auxiliares,
persistencia documental y gestión de notas conforme al estándar de LangChain/LangGraph.
"""

from pathlib import Path
from typing import List, Optional
import numpy_financial as npf
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Directorio de salida resuelto de forma modular
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. HERRAMIENTAS ARITMÉTICAS AUXILIARES (ESTILO CANÓNICO DEL CURSO)
# ==============================================================================

@tool
def sumar(a: float, b: float) -> float:
    """Suma dos números y retorna el resultado."""
    return a + b


@tool
def restar(a: float, b: float) -> float:
    """Resta b de a y retorna el resultado."""
    return a - b


@tool
def multiplicar(a: float, b: float) -> float:
    """Multiplica dos números y retorna el resultado."""
    return a * b


@tool
def dividir(a: float, b: float) -> float:
    """Divide a entre b y retorna el resultado. No se puede dividir entre cero."""
    if b == 0:
        return "Error: no se puede dividir entre cero."
    return a / b


# ==============================================================================
# 2. HERRAMIENTA FINANCIERA DETERMINISTA (EVALUACIÓN DE PROYECTO TI)
# ==============================================================================

class FinancialEvalInput(BaseModel):
    inversion_inicial: float = Field(
        description="Inversión inicial requerida para el proyecto (valor positivo)."
    )
    flujos_caja: List[float] = Field(
        description="Lista secuencial de flujos netos proyectados por periodo (ej. años)."
    )
    tasa_descuento: float = Field(
        description="Tasa de descuento anual en formato decimal (ej: 0.10 para 10%)."
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


from src.exporters import (
    exportar_informe_multiformato,
    exportar_a_docx,
    exportar_a_pdf
)

# ==============================================================================
# 3. HERRAMIENTA DE ESCRITURA Y PERSISTENCIA DOCUMENTAL (WORD, PDF Y MARKDOWN)
# ==============================================================================

class GuardarInformeInput(BaseModel):
    nombre_archivo: str = Field(
        default="dictamen_kickoff",
        description="Nombre base del archivo a crear (ej: 'dictamen_kickoff' o 'informe_kickoff.md')."
    )
    contenido_markdown: str = Field(
        description="Contenido completo del informe formal en formato Markdown a guardar y exportar."
    )
    formato: str = Field(
        default="todos",
        description="Formato de exportación: 'docx' (Word), 'pdf' (PDF), 'md' (Markdown), o 'todos' (genera los tres formatos con diseño corporativo)."
    )


@tool(args_schema=GuardarInformeInput)
def guardar_informe_kickoff(
    nombre_archivo: str,
    contenido_markdown: str,
    formato: str = "todos"
) -> str:
    """Guarda y exporta formalmente el informe final de viabilidad o especificación técnica IEEE 830
    en formatos Word (.docx), PDF (.pdf) y Markdown (.md) en el directorio de salida (output/).
    Utilízalo obligatoriamente cuando el usuario solicite guardar, formalizar, generar o exportar a Word, PDF o archivo."""
    try:
        # Si el usuario pasa explícitamente una extensión en el nombre, respetar el formato
        clean_ext = Path(nombre_archivo).suffix.lower()
        if clean_ext in [".docx", ".pdf", ".md"]:
            formato_efectivo = clean_ext.replace(".", "") if formato == "todos" else formato
        else:
            formato_efectivo = formato

        resultado = exportar_informe_multiformato(
            contenido_markdown=contenido_markdown,
            nombre_base=nombre_archivo,
            directorio_salida=OUTPUT_DIR,
            formato=formato_efectivo
        )

        archivos = resultado.get("archivos", {})
        errores = resultado.get("errores", [])

        if not archivos and errores:
            return f"Error al generar informe: {'; '.join(errores)}"

        detalles_archivos = "\n".join([f"- **{fmt.upper()}:** `{ruta}`" for fmt, ruta in archivos.items()])
        mensaje_salida = f"Informe guardado exitosamente en los siguientes formatos:\n{detalles_archivos}"

        if errores:
            mensaje_salida += f"\n\n*Advertencias durante la exportación:* {'; '.join(errores)}"

        return mensaje_salida
    except Exception as e:
        return f"Error al guardar el informe: {str(e)}"


# ==============================================================================
# 4. HERRAMIENTA DE EDICIÓN DE NOTAS
# ==============================================================================

class EditarNotaInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre del archivo .md o .txt existente a editar (ej: 'dictamen_kickoff.md')."
    )
    nuevo_contenido: str = Field(
        description="Contenido completo que reemplazará el archivo existente."
    )


@tool(args_schema=EditarNotaInput)
def editar_nota_kickoff(nombre_archivo: str, nuevo_contenido: str) -> str:
    """Edita (sobrescribe) el contenido de un archivo existente en el directorio output/.
    Úsalo cuando el usuario pida modificar, actualizar o corregir un documento guardado."""
    try:
        clean_name = Path(nombre_archivo).name
        target_path = OUTPUT_DIR / clean_name
        if not target_path.exists():
            archivos = [f.name for f in OUTPUT_DIR.iterdir() if f.is_file()]
            return f"Archivo '{clean_name}' no encontrado. Archivos disponibles: {archivos}"
        target_path.write_text(nuevo_contenido, encoding="utf-8")
        return f"Archivo '{clean_name}' actualizado exitosamente en: {target_path}"
    except Exception as e:
        return f"Error al editar el archivo: {str(e)}"


# ==============================================================================
# 5. HERRAMIENTA DE ELIMINACIÓN DE NOTAS
# ==============================================================================

class EliminarNotaInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre del archivo a eliminar del directorio output/ (ej: 'borrador.md')."
    )


@tool(args_schema=EliminarNotaInput)
def eliminar_nota_kickoff(nombre_archivo: str) -> str:
    """Elimina un archivo guardado en el directorio output/.
    Úsalo cuando el usuario pida eliminar, borrar o descartar un documento generado."""
    try:
        clean_name = Path(nombre_archivo).name
        target_path = OUTPUT_DIR / clean_name
        if not target_path.exists():
            return f"El archivo '{clean_name}' no existe en output/."
        target_path.unlink()
        return f"Archivo '{clean_name}' eliminado correctamente."
    except Exception as e:
        return f"Error al eliminar el archivo: {str(e)}"


# ==============================================================================
# 6. HERRAMIENTA DE RESUMEN DE SESIÓN
# ==============================================================================

class ExportarSesionInput(BaseModel):
    nombre_archivo: Optional[str] = Field(
        default="resumen_sesion.md",
        description="Nombre del archivo de resumen (por defecto 'resumen_sesion.md')."
    )
    contenido_resumen: str = Field(
        description="Texto completo del resumen de la sesión actual en formato Markdown."
    )


@tool(args_schema=ExportarSesionInput)
def exportar_resumen_sesion(nombre_archivo: str, contenido_resumen: str) -> str:
    """Exporta un resumen estructurado de la sesión de conversación actual a un archivo Markdown en output/.
    Úsalo cuando el usuario pida exportar, resumir o guardar el historial de la conversación."""
    try:
        import datetime
        clean_name = Path(nombre_archivo).name
        if not clean_name.endswith(".md"):
            clean_name += ".md"
        target_path = OUTPUT_DIR / clean_name
        encabezado = (
            f"# Resumen de Sesión — KickoffAgent\n"
            f"_Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n---\n\n"
        )
        target_path.write_text(encabezado + contenido_resumen, encoding="utf-8")
        return f"Resumen de sesión guardado en: {target_path}"
    except Exception as e:
        return f"Error al exportar el resumen: {str(e)}"
