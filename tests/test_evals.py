from eval.run_evals import (
    _parsear_json,
    _promedio,
    extraer_herramientas,
    extraer_respuesta,
    juzgar_rag,
    tool_call_accuracy,
)


class Mensaje:
    def __init__(self, contenido="", nombre=None, llamadas=None):
        self.content = contenido
        self.name = nombre
        self.tool_calls = llamadas or []


def test_parsear_json_con_fences():
    assert _parsear_json('```json\n{"score": 0.8}\n```') == {"score": 0.8}


def test_parsear_json_invalido():
    assert _parsear_json("no es json") == {}


def test_tool_call_accuracy():
    assert tool_call_accuracy(["sumar"], ["sumar", "dividir"]) is True
    assert tool_call_accuracy(["sumar", "dividir"], ["sumar"]) is False


def test_extraer_herramientas():
    resultado = {"messages": [
        Mensaje(llamadas=[{"name": "consultar_documentacion_proyecto"}]),
        Mensaje("fuente", "consultar_documentacion_proyecto"),
    ]}
    assert extraer_herramientas(resultado) == ["consultar_documentacion_proyecto"]


def test_extraer_respuesta_ignora_tool_messages():
    resultado = {"messages": [
        Mensaje("fuente", "consultar_documentacion_proyecto"),
        Mensaje("respuesta final"),
    ]}
    assert extraer_respuesta(resultado) == "respuesta final"


def test_promedio_ignora_valores_no_aplicables():
    assert _promedio([1.0, None, 0.5]) == 0.75


def test_rag_metrics_no_aplican_sin_contexto():
    class JuezInactivo:
        def invoke(self, prompt):
            raise AssertionError("No se debe llamar al juez sin contexto")

    assert juzgar_rag("pregunta", "", "respuesta", JuezInactivo()) == (None, None)
