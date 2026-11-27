# prompts/

Contiene las plantillas de prompts de diseño de KickoffAgent.

Estado actual: estos archivos son artefactos de documentación del diseño. El agente no los carga en tiempo de ejecución. El prompt que realmente usa el grafo está en `src/prompts.py`, en la constante `AGENT_SYSTEM_PROMPT`.

## Archivos

- `prompt_01.md`: levantamiento FODA y PESTEL.
- `prompt_02.md`: clasificador de evidencia de apoyo por fragmento.
- `prompt_03.md`: extracción de requerimientos funcionales y no funcionales, formato IEEE 830.
- `prompt_04.md`: generación de backlog Scrum.
- `prompt_05.md`: respuesta RAG para onboarding de proyecto.
