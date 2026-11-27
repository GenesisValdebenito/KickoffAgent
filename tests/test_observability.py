import observability.logger as logger
import observability.metrics as metrics


def test_registrar_ejecucion_escribe_jsonl(tmp_path, monkeypatch):
    archivo = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logger, "LOG_FILE", archivo)

    registro = logger.registrar_ejecucion(
        thread_id="hilo_prueba",
        entrada=[("user", "hola")],
        resultado={"messages": []},
        latencia_ms=12.5,
    )

    assert registro["ruta"] == "directa"
    assert registro["latencia_ms"] == 12.5
    assert len(logger.leer_logs()) == 1


def test_detecta_ruta_rag(tmp_path, monkeypatch):
    archivo = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logger, "LOG_FILE", archivo)

    class Mensaje:
        name = "consultar_documentacion_proyecto"
        content = "--- Fuente: Acta_Reunion_01.pdf ---\nPresupuesto 12.000.000"
        tool_calls = []

    registro = logger.registrar_ejecucion(
        thread_id="hilo_rag",
        entrada=[("user", "presupuesto")],
        resultado={"messages": [Mensaje()]},
        latencia_ms=30,
    )

    assert registro["ruta"] == "rag"
    assert registro["herramientas"] == ["consultar_documentacion_proyecto"]
    assert registro["chunks_recuperados"] == 1


def test_calcular_costo(monkeypatch):
    monkeypatch.setenv("PRICE_INPUT_PER_1M", "1")
    monkeypatch.setenv("PRICE_OUTPUT_PER_1M", "2")

    assert metrics.calculate_cost(1_000_000, 1_000_000) == 3.0


def test_medir_latencia():
    with metrics.medir_latencia() as medicion:
        sum(range(1000))

    assert medicion["latencia_ms"] >= 0
