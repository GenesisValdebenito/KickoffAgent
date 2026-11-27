# Dashboard de observabilidad

Hay dos opciones. Streamlit funciona sin servicios externos. Grafana LGTM es la opción del profesor y consume los datos de Supabase.

## Opción A, Streamlit

Lee directamente `logs/agent_logs.jsonl`.

```bash
streamlit run dashboard/app.py
```

Muestra ejecuciones, errores, latencia promedio y p95, rutas, herramientas, tabla filtrable y registro JSONL.

## Opción B, Grafana LGTM + Supabase

```bash
docker compose -f dashboard/docker-compose.yml up -d
```

Variables en `.env` o en el entorno:

```text
GF_ADMIN_PASSWORD=admin
SUPABASE_DB_HOST=db.TU_PROYECTO.supabase.co
SUPABASE_DB_PORT=6543
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=TU_PASSWORD
```

Grafana: `http://localhost:3000`. El panel `KickoffAgent — Observabilidad` queda provisionado desde `dashboards/kickoff-agent.json` y el datasource Postgres desde `provisioning/datasources/datasources.yml`.

El contenedor también expone OTLP en `4317` y `4318`. Para activar trazas de LangChain:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

`observability/telemetry.py` configura el exportador y el instrumentador cuando las dependencias están disponibles. Si no lo están, el logger JSONL sigue funcionando.

## Flujo de datos

```text
agente → logs/agent_logs.jsonl → W3 (n8n) → Supabase logs → Grafana
       → eval/results.json    → W1 (n8n) → Supabase evals  → Grafana
       → /metrics             → W2 (n8n) → alerta Telegram
```
