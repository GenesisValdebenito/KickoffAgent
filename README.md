# KickoffAgent

KickoffAgent es un agente inteligente para firmas de consultoría tecnológica e ingeniería de software. Asiste en la etapa inicial de un proyecto mediante análisis documental con RAG y evaluación financiera determinista.

El proyecto se desarrolló para la asignatura Ingeniería de Soluciones con Inteligencia Artificial. El repositorio es público en `https://github.com/GenesisValdebenito/KickoffAgent`.

## Capacidades

1. Análisis de requerimientos con RAG. Ingesta de actas, especificaciones IEEE 830 y archivos PDF, TXT, MD, CSV o JSON. Extrae requerimientos funcionales y no funcionales en formato de historias de usuario y cita la fuente.
2. Evaluación financiera determinista. Extrae inversión inicial, flujos de caja y tasa de descuento desde los documentos, y delega el cálculo de VAN, TIR, ROI y PRI en `numpy-financial`. El modelo no calcula estos valores en texto.
3. Orquestación con LangGraph. Un grafo con nodos `agent` y `tools` decide de forma autónoma si invoca RAG, cálculo financiero, persistencia u operaciones aritméticas.
4. Memoria conversacional. Memoria de corto plazo con `MemorySaver` por `thread_id` y persistencia de sesiones en JSON dentro de `sessions/`.

## Arquitectura

- Modelo principal: Groq `qwen/qwen3.8-27b`, temperatura 0. Alternativa: OpenAI `gpt-4o-mini`.
- Embeddings: FastEmbed `BAAI/bge-small-en-v1.5`, ejecución local.
- Vector store: ChromaDB, colección `kickoff_agent_knowledge`, recuperación `k=4`.
- Grafo: LangGraph `StateGraph`, `ToolNode`, arista condicional `should_continue`.
- Herramientas: 10 en total, definidas en `src/tools.py`.
- Prompt del sistema: `AGENT_SYSTEM_PROMPT` en `src/prompts.py`.
- Observabilidad: registros JSONL en `logs/agent_logs.jsonl`, métricas y trazas OTEL opcionales.
- Evaluación: `eval/run_evals.py` con juez LLM y métricas tipo RAGAS.
- Seguridad: cinco guardrails de entrada y uno de salida en `guardrails/`.
- Automatización: n8n con tres workflows, sin reemplazar la orquestación de LangGraph.

No existe modo demostración. Para ejecutar el agente se requiere una API key válida. Si no está configurada, el programa lo indica y termina.

## Estructura real del proyecto

```text
KickoffAgent/
├── src/
│   ├── kickoff_agent.py    # grafo, RAG, LLM y consola interactiva
│   ├── tools.py            # herramientas del agente
│   ├── prompts.py          # prompt del sistema usado por el grafo
│   └── memory.py           # persistencia de sesiones
├── observability/
│   ├── logger.py           # registro JSONL de ejecuciones
│   ├── metrics.py          # latencia, tokens, costo y errores
│   └── telemetry.py        # trazas OTEL opcionales para Grafana LGTM
├── eval/
│   ├── dataset.json        # 15 casos de evaluación funcional
│   ├── run_evals.py        # juez LLM, RAGAS-style y consistencia de herramientas
│   ├── consistencia.py     # repetición de casos y varianza
│   └── results.json        # resultados de la última corrida
├── guardrails/
│   ├── guardrails.py       # 5 evaluadores de entrada + 1 de salida
│   └── prompts.py          # prompts de los evaluadores
├── api/
│   └── server.py           # FastAPI: /health, /ask, /metrics, /logs, /eval
├── dashboard/
│   ├── app.py              # panel Streamlit sobre el JSONL
│   ├── docker-compose.yml  # Grafana LGTM
│   ├── dashboards/         # panel provisionado de Grafana
│   └── provisioning/       # datasource de Supabase Postgres
├── integrations/
│   └── supabase_logger.py  # carga de logs y evaluaciones por REST
├── n8n/
│   ├── docker-compose.yml
│   ├── workflows/          # W1 eval loop, W2 alertas, W3 carga de logs
│   └── README.md
├── supabase/
│   └── schema.sql          # tablas logs, evals y metricas
├── prompts/                # plantillas de diseño, no cargadas en ejecución
│   ├── prompt_01.md
│   ├── prompt_02.md
│   ├── prompt_03.md
│   ├── prompt_04.md
│   └── prompt_05.md
├── docs/                   # informes y diagramas
├── tests/                  # pytest y capturas de evidencia
├── logs/                   # registros generados en ejecución
├── sessions/               # sesiones persistidas
├── output/                 # informes generados por el agente
├── requirements.txt
└── README.md
```

Los archivos de `prompts/` son artefactos de documentación del diseño. El único prompt cargado por el código es `AGENT_SYSTEM_PROMPT` en `src/prompts.py`.

## Instalación

```bash
git clone https://github.com/GenesisValdebenito/KickoffAgent.git
cd KickoffAgent
python -m venv .venv
pip install -r requirements.txt
```

Crear un archivo `.env` en la raíz:

```text
GROQ_API_KEY=tu_clave_gsk
```

También se admite `OPENAI_API_KEY`. El archivo `.env` está ignorado por Git.

Variables opcionales para observabilidad y automatización:

```text
PRICE_INPUT_PER_1M=0
PRICE_OUTPUT_PER_1M=0
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_SERVICE_KEY=TU_SERVICE_ROLE_KEY
```

## Ejecución

Modo interactivo:

```bash
python src/kickoff_agent.py
```

Indexar un documento al iniciar:

```bash
python src/kickoff_agent.py "docs/Informe_Tecnico_KickoffAgent.pdf"
```

Ejecutar pruebas unitarias:

```bash
python -m pytest -v tests/
```

También funciona:

```bash
python src/kickoff_agent.py --test
```

Al iniciar, el programa solicita la ruta de un documento. Si se presiona ENTER, indexa los archivos de `docs/`. Luego ofrece continuar una sesión previa o crear una nueva.

## Comandos interactivos

- `/cargar <ruta>` indexa un documento en caliente.
- `/documentos` lista los documentos activos.
- `/historial` muestra el historial de la sesión.
- `/exportar` guarda el historial en `output/`.
- `/sesiones` lista y gestiona sesiones guardadas.
- `/limpiar` reinicia la memoria conversacional.
- `/test` ejecuta la batería de pruebas con pytest.
- `/ayuda` muestra el menú.
- `salir` guarda la sesión y termina.

## Observabilidad

Cada invocación del grafo escribe una línea en `logs/agent_logs.jsonl` con: timestamp, `trace_id`, `thread_id`, ruta elegida, herramientas invocadas, fragmentos recuperados, latencia, tokens, salida y errores.

Las utilidades de medición están en `observability/metrics.py`. Incluyen context manager de latencia, resumen de tokens, cálculo de costo según precios configurados en `.env` y registro de errores.

## API

Levantar el servidor:

```bash
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`: estado del agente y documentos registrados.
- `POST /ask`: cuerpo con `pregunta` y `thread_id` opcional.
- `GET /metrics`: ejecuciones, errores, latencia promedio y p95, rutas y herramientas más usadas.
- `GET /logs`: eventos JSONL para que n8n los cargue en Supabase.
- `POST /eval`: ejecuta el dataset con LLM real y guarda `eval/results.json`.

Todas las peticiones a `/ask` pasan por los guardrails antes y después del agente.

## Evaluación

`eval/dataset.json` contiene 15 casos con pregunta, referencia, herramientas esperadas y fuente esperada. Cubre las categorías RAG, finanzas, persistencia, rechazo y aritmética.

```bash
python -m eval.run_evals
python -m eval.run_evals --limite 5
python -m eval.run_evals --caso pers_001 --fusionar
python -m eval.consistencia
python -m eval.consistencia --caso ari_001 --fusionar
```

Métricas calculadas:

- Tool Call Accuracy: el agente invocó las herramientas esperadas.
- Agent Goal Accuracy: un juez LLM compara la respuesta con la referencia.
- Faithfulness y Answer Relevancy: jueces LLM sobre el contexto RAG recuperado, siguiendo la definición de RAGAS. No se instala la librería `ragas` para evitar incompatibilidades con LangChain 1.x.
- El juez se crea en `judges/juez.py`. Usa `OPENAI_API_KEY` con `gpt-4o-mini` si está configurada; si no, usa Groq. El agente evaluado no cambia. En `results.json` queda registrado el proveedor del juez.
- Latencia por caso, p95, tasa de error y consistencia de la tool financiera.

Los reintentos con espera en `eval/run_evals.py` absorben los límites de tokens por minuto de Groq. Si un caso falla por límite ITPM u OTPM, se puede repetir solo ese caso con `--caso ID --fusionar`, sin perder el resto de la corrida. Para una corrida corta, usar `--limite 5`. El caso `pers_001` pide un dictamen breve porque un documento extenso en el historial supera el techo de 7000 tokens de entrada de Groq.

En la corrida de consistencia, `fin_003` y `rag_003` completaron las cinco repeticiones con accuracy 1.0 y desviaciones de 9895 ms y 3005 ms. `ari_001` quedó limitado por la cuota diaria de Groq (TPD 200000) y se registró como anomalía de infraestructura en `eval/consistencia.json`. Mover el juez a OpenAI reduce el consumo de Groq en las evaluaciones, pero no cambia el hecho de que la prueba de consistencia llama al agente Groq directamente.

## Guardrails

`guardrails/guardrails.py` evalúa ofensivo, prompt injection, off topic, deshonestidad y PII antes de llamar al agente, y una validación de salida después. Las peticiones bloqueadas devuelven HTTP 400.

Los evaluadores usan el mismo LLM con temperatura 0 y se ejecutan en paralelo. Si el juez no responde, el guardrail no bloquea y el evento debe revisarse en el log. En producción conviene cambiar ese comportamiento a fail closed.

## Dashboard

```bash
streamlit run dashboard/app.py
```

Alternativa con Grafana LGTM y Supabase en `dashboard/docker-compose.yml`. Las instrucciones están en `dashboard/README.md`.

## Supabase y n8n

Ejecutar `supabase/schema.sql` en el proyecto de Supabase y definir `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`. Luego levantar n8n con `n8n/docker-compose.yml` e importar los tres workflows desde `n8n/workflows/`.

- W1: evaluación periódica y carga en `evals`.
- W2: alertas por tasa de error y latencia p95.
- W3: carga de logs en `logs`.

n8n no es el agente ni el orquestador. LangGraph decide el razonamiento; n8n automatiza el ciclo de observabilidad.

La evidencia visual de ejecución se encuentra en `tests/Evidencia_Tests.md` y las capturas `test_01.png` a `test_04-2.png`.
