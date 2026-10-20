import pytest
import numpy_financial as npf
from src.kickoff_agent import (
    calcular_metricas_financieras,
    inicializar_vectorstore,
    consultar_documentacion_proyecto,
    agent_executor
)

def test_herramienta_financiera_van_positivo():
    """Valida el cálculo determinista de métricas con flujos de proyecto viable."""
    resultado = calcular_metricas_financieras.invoke({
        "inversion_inicial": 12000000.0,
        "flujos_caja": [4500000.0, 5000000.0, 6200000.0],
        "tasa_descuento": 0.10
    })
    
    assert resultado["inversion_inicial"] == 12000000.0
    assert resultado["van"] == 881292.26
    assert resultado["tir"] == "13.9%"
    assert resultado["roi_porcentual"] == "30.83%"
    assert resultado["pri_estimado"] == "3 periodos"
    assert "Financieramente Viable" in resultado["conclusion_tecnica"]

def test_herramienta_financiera_van_negativo():
    """Valida el rechazo determinista ante proyecto con pérdida."""
    resultado = calcular_metricas_financieras.invoke({
        "inversion_inicial": 10000000.0,
        "flujos_caja": [1000000.0, 1000000.0, 1000000.0],
        "tasa_descuento": 0.15
    })
    
    assert resultado["van"] < 0
    assert "No Viable" in resultado["conclusion_tecnica"]

def test_recuperacion_semantica_rag():
    """Valida que el vectorstore y el retriever recuperen documentos con metadatos."""
    vs = inicializar_vectorstore()
    retriever = vs.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke("OAuth2 autenticacion")
    
    assert len(docs) > 0
    assert any("OAuth2" in d.page_content for d in docs)
    assert any(d.metadata.get("source") for d in docs)

def test_consultar_documentacion_tool():
    """Valida la ejecución de la Tool que expone el agente."""
    salida = consultar_documentacion_proyecto.invoke({"consulta": "presupuesto limite"})
    assert "Fuente:" in salida
    assert "12.000.000" in salida

def test_orquestador_ejecucion_mensajes():
    """Valida que el agente orquestador responda si hay API key configurada."""
    import os
    if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY").startswith("tu_clave"):
        pytest.skip("GROQ_API_KEY no configurada en este entorno (ej. CI sin Secret)")
    
    respuesta = agent_executor.invoke(
        {"messages": [("user", "Hola, preséntate brevemente y di qué rol tienes.")]},
        config={"configurable": {"thread_id": "test_thread_basico"}}
    )
    mensajes = respuesta.get("messages", [])
    assert len(mensajes) >= 2
    ultimo_mensaje = mensajes[-1].content
    assert len(ultimo_mensaje) > 0

def test_herramienta_escritura_informe(tmp_path):
    """Valida que la tool de escritura persista archivos correctamente en output/."""
    from src.kickoff_agent import guardar_informe_kickoff, OUTPUT_DIR
    nombre = "test_informe_salida.md"
    contenido = "# Acta de Prueba\nVAN positivo y viable."
    resultado = guardar_informe_kickoff.invoke({
        "nombre_archivo": nombre,
        "contenido_markdown": contenido
    })
    
    assert "Informe guardado exitosamente" in resultado
    archivo_creado = OUTPUT_DIR / nombre
    assert archivo_creado.exists()
    assert "VAN positivo" in archivo_creado.read_text(encoding="utf-8")
    # Limpiar archivo de prueba
    if archivo_creado.exists():
        archivo_creado.unlink()

def test_continuidad_memoria_corto_plazo():
    """Valida que el MemorySaver mantenga el hilo de conversación entre turnos."""
    import os
    if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY").startswith("tu_clave"):
        pytest.skip("GROQ_API_KEY no configurada en este entorno")
        
    thread_config = {"configurable": {"thread_id": "test_memoria_turnos"}}
    
    # Turno 1: Definir un dato clave en la conversación
    agent_executor.invoke(
        {"messages": [("user", "El nombre clave del proyecto confidencial es 'Operación Cóndor 2026'.")]},
        config=thread_config
    )
    
    # Turno 2: Preguntar por el dato sin repetirlo
    res_turno_2 = agent_executor.invoke(
        {"messages": [("user", "¿Cuál es el nombre clave del proyecto que te acabo de decir?")]},
        config=thread_config
    )
    
    respuesta_2 = res_turno_2["messages"][-1].content
    assert "Cóndor" in respuesta_2 or "Condor" in respuesta_2
