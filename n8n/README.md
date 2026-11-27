# n8n — capa de automatización

n8n **no reemplaza al agente**. LangGraph sigue siendo el orquestador del razonamiento. n8n automatiza el ciclo de observabilidad: ejecuta evaluaciones, carga datos en Supabase y dispara alertas.

## Levantar n8n

```bash
docker run -d --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=cambiar_clave \
  -e KICKOFF_API_URL=http://host.docker.internal:8000 \
  -e SUPABASE_URL=https://TU_PROYECTO.supabase.co \
  -e SUPABASE_SERVICE_KEY=TU_SERVICE_ROLE_KEY \
  -e UMBRAL_TASA_ERROR=0.1 \
  -e UMBRAL_P95_MS=30000 \
  -e TELEGRAM_BOT_TOKEN=TU_TOKEN \
  -e TELEGRAM_CHAT_ID=TU_CHAT_ID \
  docker.n8n.io/n8nio/n8n
```

En Linux, reemplazar `host.docker.internal` por `172.17.0.1` o usar `--network host`.

UI: `http://localhost:5678`.

También está `docker-compose.yml` con la misma configuración:

```bash
docker compose -f n8n/docker-compose.yml up -d
```

## Importar los workflows

En la UI: `Workflows → Import from File` y seleccionar cada JSON de `n8n/workflows/`. Quedan en estado inactivo. Activarlos con el toggle cuando la API y Supabase estén disponibles.

| Workflow | Trigger | Flujo | Indicador |
|---|---|---|---|
| `W1_eval_loop.json` | Cada 60 min | `POST /eval` → prepara resumen → inserta en `evals` | IE3, IE6, IE7 |
| `W2_alertas.json` | Cada 15 min | `GET /metrics` → evalúa umbrales → Telegram si supera | IE3, IE4, IE7 |
| `W3_carga_logs.json` | Cada 30 min | `GET /logs` → mapea eventos → inserta en `logs` | IE4 |

## Variables de entorno

| Variable | Uso |
|---|---|
| `KICKOFF_API_URL` | Base de la FastAPI, sin barra final |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_SERVICE_KEY` | Service role key, bypassa RLS |
| `UMBRAL_TASA_ERROR` | Tasa de error que dispara alerta, por defecto 0.1 |
| `UMBRAL_P95_MS` | Latencia p95 que dispara alerta, por defecto 30000 |
| `TELEGRAM_BOT_TOKEN` | Token del bot para W2 |
| `TELEGRAM_CHAT_ID` | Chat destino de W2 |

## Verificación manual

```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
curl "http://localhost:8000/logs?limite=5"
curl -X POST "http://localhost:8000/eval?limite=5"
```

Si W3 no inserta, revisar que `supabase/schema.sql` se haya ejecutado y que la service key tenga permisos de inserción.
