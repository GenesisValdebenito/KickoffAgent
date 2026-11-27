"""Instrumentación OpenTelemetry opcional para KickoffAgent.

Si el collector OTLP está disponible, los spans de LangChain se exportan a Grafana LGTM.
Si no lo está, el módulo queda inactivo y el logger JSONL sigue funcionando.
"""

import os
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

_inicializado = False


def configurar_telemetria(servicio: str = "kickoff-agent") -> bool:
    """Configura el tracer provider y el instrumentador de LangChain.

    Devuelve True si la instrumentación quedó activa.
    """
    global _inicializado
    if _inicializado:
        return True

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317").strip()
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return False

    provider = TracerProvider(resource=Resource.create({"service.name": servicio}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

    try:
        from opentelemetry.instrumentation.langchain import LangchainInstrumentor
        LangchainInstrumentor().instrument()
    except ImportError:
        pass

    _inicializado = True
    return True


def tracer(nombre: str = "kickoff-agent") -> Optional[object]:
    """Devuelve un tracer de OpenTelemetry o None si no hay instrumentación."""
    if not configurar_telemetria():
        return None
    from opentelemetry import trace
    return trace.get_tracer(nombre)
