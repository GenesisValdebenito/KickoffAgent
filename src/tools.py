"""Módulo de Herramientas (Tools) del Agente KickoffAgent.
Define las herramientas de cálculo determinista, operaciones matemáticas auxiliares
y persistencia documental conforme al estándar de LangChain/LangGraph.
"""

from pathlib import Path
from typing import List
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


# ==============================================================================
# 3. HERRAMIENTA DE ESCRITURA Y PERSISTENCIA DOCUMENTAL
# ==============================================================================

class GuardarInformeInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre del archivo a crear con extension .md o .txt (ej: 'dictamen_kickoff.md')."
    )
    contenido_markdown: str = Field(
        description="Contenido completo del informe formal en formato Markdown a guardar."
    )


@tool(args_schema=GuardarInformeInput)
def guardar_informe_kickoff(nombre_archivo: str, contenido_markdown: str) -> str:
    """Guarda formalmente el informe final de viabilidad o especificación técnica IEEE 830
    en el directorio de salida del proyecto (output/). Utilízalo cuando el usuario pida
    generar, formalizar, guardar o exportar el documento del proyecto."""
    try:
        clean_name = Path(nombre_archivo).name
        if not (clean_name.endswith(".md") or clean_name.endswith(".txt")):
            clean_name += ".md"
        
        target_path = OUTPUT_DIR / clean_name
        target_path.write_text(contenido_markdown, encoding="utf-8")
        return f"Informe guardado exitosamente en: {target_path}"
    except Exception as e:
        return f"Error al guardar el informe: {str(e)}"
