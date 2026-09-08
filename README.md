# KickoffAgent

Evaluación Parcial N°1 — Desarrollo de Agentes Inteligentes con LLM (DuocUC)

**Plataforma de agentes inteligentes que guía el levantamiento de antecedentes de un proyecto de software, sistematiza su análisis de viabilidad preliminar (FODA/PESTEL), lo traduce automáticamente en un backlog ágil ejecutable, y permite consultarlo todo por chat de forma trazable (RAG).**

Inspirado en cómo plataformas de cumplimiento normativo (p. ej. [Dani](https://github.com/EliasVicencio19/Dani-ISO27001), para ISO 27001) usan agentes de IA para transformar un levantamiento estructurado en documentación formal y en un repositorio consultable — aplicamos el mismo patrón al dominio de formulación y evaluación de proyectos de software.

## Pipeline (3 etapas, 2 agentes + RAG)

1. **Agente de Levantamiento** — el usuario responde un cuestionario (antecedentes, partes interesadas, problema/oportunidad) y sube evidencia de apoyo (entrevistas, benchmarking). El agente sistematiza esto en un análisis **FODA + PESTEL** y clasifica automáticamente la evidencia por categoría.
2. **Agente Generador de Backlog** — toma el documento de Antecedentes + Necesidades, extrae RF/RNF y genera **épicas → historias de usuario → tareas → sprints**.
3. **Módulo RAG** — indexa el análisis, la evidencia y el backlog para que cualquier interesado consulte el proyecto por chat, con respuestas ancladas en evidencia real y citas trazables.

## Por qué está diseñado así

Un sistema RAG conversacional por sí solo responde preguntas, pero no **ejecuta** ninguna tarea — no es un agente. El núcleo de PlanAgiDev son los dos agentes que transforman información (levantamiento → análisis, análisis → backlog); el RAG se mantiene como módulo de soporte (consulta y trazabilidad), no como el corazón del sistema. Ver el detalle completo de esta decisión en `docs/informe-tecnico.docx`.

## Estructura del repositorio

```
proyecto/
├── README.md
├── docs/
│   └── informe-tecnico.docx     # Informe técnico completo (contexto, objetivos,
│                                  #   prompts, arquitectura, restricciones, referencias APA)
├── diagramas/
│   ├── arquitectura_v3.png      # Diagrama de arquitectura (pipeline de 3 etapas)
│   └── gen_diagrama_v3.py       # Script que genera el diagrama
├── prompts/
│   ├── 00_levantamiento_foda_pestel.md
│   ├── 01_extraccion_rf_rnf.md
│   ├── 02_generacion_backlog.md
│   └── 03_rag_respuesta.md
├── src/
│   ├── agente_backlog/          # Lógica de generación de backlog
│   ├── rag/                     # Pipeline RAG (index, embeddings, retriever)
│   └── api/                     # Endpoints de la aplicación
└── tests/
```

## Alcance del MVP (primera entrega)

- ✅ Levantamiento de información y evaluación preliminar (FODA + PESTEL)
- ✅ Formulación ágil (backlog generado por agente)
- ✅ RAG de consulta con trazabilidad (Faithfulness / Answer Relevancy)
- 🔜 Roadmap: estudio financiero (VAN, TIR, PRI, ROI), estudios técnico/mercado/organizacional, integraciones externas (Git, Jira)

## Estado actual

- [x] Propuesta revisada y aprobada por el docente
- [x] Informe técnico
- [x] Diagrama de arquitectura
- [x] Prompts diseñados y justificados (0, 1, 2, 3)
- [ ] Implementación del Agente de Levantamiento
- [ ] Implementación del Agente Generador de Backlog
- [ ] Implementación del pipeline RAG
- [ ] Métricas de calidad (Faithfulness / Answer Relevancy)
- [ ] Defensa oral
