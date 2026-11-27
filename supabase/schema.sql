-- Esquema mínimo para la observabilidad de KickoffAgent en Supabase.
-- Ejecutar en el SQL Editor del proyecto.

create table if not exists public.logs (
  id bigint generated always as identity primary key,
  trace_id text,
  thread_id text,
  tipo text,
  timestamp timestamptz,
  ruta text,
  herramientas jsonb default '[]'::jsonb,
  chunks_recuperados integer default 0,
  latencia_ms numeric,
  tokens jsonb default '{}'::jsonb,
  error text,
  salida text,
  creado_en timestamptz default now()
);

create table if not exists public.evals (
  id bigint generated always as identity primary key,
  fecha timestamptz,
  resumen jsonb default '{}'::jsonb,
  detalle jsonb default '[]'::jsonb,
  creado_en timestamptz default now()
);

create table if not exists public.metricas (
  id bigint generated always as identity primary key,
  fecha timestamptz default now(),
  total_ejecuciones integer,
  total_errores integer,
  tasa_error numeric,
  latencia_promedio_ms numeric,
  latencia_p95_ms numeric,
  herramientas jsonb default '{}'::jsonb,
  rutas jsonb default '{}'::jsonb
);

alter table public.logs enable row level security;
alter table public.evals enable row level security;
alter table public.metricas enable row level security;

-- La service_role key bypassa RLS. Estas políticas permiten lectura con anon key si se necesita.
create policy "lectura_logs" on public.logs for select using (true);
create policy "lectura_evals" on public.evals for select using (true);
create policy "lectura_metricas" on public.metricas for select using (true);
