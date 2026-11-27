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
- Observabilidad: registros JSONL en `logs/agent_logs.jsonl`.

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
│   └── metrics.py          # latencia, tokens, costo y errores
├── eval/
│   └── dataset.json        # 15 casos de evaluación funcional
├── api/
│   └── server.py           # FastAPI: /health, /ask, /metrics, /eval
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
- `POST /eval`: ejecuta el dataset y guarda `eval/results.json`.

## Evaluación

`eval/dataset.json` contiene 15 casos con pregunta, referencia, herramientas esperadas y fuente esperada. Cubre las categorías RAG, finanzas, persistencia, rechazo y aritmética.

La evidencia visual de ejecución se encuentra en `tests/Evidencia_Tests.md` y las capturas `test_01.png` a `test_04-2.png`.
