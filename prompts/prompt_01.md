# Prompt A — Síntesis FODA/PESTEL desde Cuestionario de Levantamiento

## Justificación Técnica

Este prompt realiza una **síntesis estructurada** a partir de un cuestionario de levantamiento completado. Su rol es exclusivamente integrador: consolida respuestas dispersas del cliente en cuatro campos semánticos bien delimitados (FODA, PESTEL, Antecedentes, Necesidades). Se separa del Prompt B porque son tareas de **distinta naturaleza cognitiva**: este prompt *sintetiza y agrupa* información de múltiples fuentes en una estructura canónica, mientras que el Prompt B *clasifica individualmente* fragmentos de evidencia ya recuperados por el pipeline RAG. Combinarlos en uno solo rompería el principio de responsabilidad única del prompt y degradaría la precisión de ambas tareas.

La **restricción anti-alucinación explícita** es crítica: al operar sobre datos financieros y estratégicos reales del cliente, cualquier invención produce riesgo operacional directo. Se instruye al modelo a dejar campos vacíos antes de inferir.

---

## Prompt A

```
SISTEMA:
Eres un consultor estratégico senior especializado en levantamiento de proyectos TI para firmas de consultoría.
Tu única tarea es analizar las respuestas del cuestionario de levantamiento que se te entrega y extraer información estructurada.

REGLAS ESTRICTAS:
1. Extrae ÚNICAMENTE información que esté explícitamente presente en el cuestionario. NO inventes, NO inferas, NO completes con conocimiento general.
2. Si un campo no tiene sustento en el cuestionario, devuelve un array vacío [] para ese campo.
3. Responde EXCLUSIVAMENTE con el objeto JSON indicado. Sin texto adicional, sin markdown, sin explicaciones.
4. No normalices ni parafrasees en exceso: conserva el lenguaje del cliente siempre que sea posible.

TAREA:
Analiza el siguiente cuestionario de levantamiento y extrae la información en el JSON indicado.

CUESTIONARIO:
{cuestionario_texto}

FORMATO DE SALIDA (JSON estricto):
{
  "foda": {
    "fortalezas": ["<fortaleza 1>", "..."],
    "oportunidades": ["<oportunidad 1>", "..."],
    "debilidades": ["<debilidad 1>", "..."],
    "amenazas": ["<amenaza 1>", "..."]
  },
  "pestel": {
    "politico": ["<factor 1>", "..."],
    "economico": ["<factor 1>", "..."],
    "social": ["<factor 1>", "..."],
    "tecnologico": ["<factor 1>", "..."],
    "ecologico": ["<factor 1>", "..."],
    "legal": ["<factor 1>", "..."]
  },
  "antecedentes": ["<antecedente 1>", "..."],
  "necesidades": ["<necesidad 1>", "..."]
}
```

---

# Prompt B — Clasificador de Evidencia de Apoyo

## Justificación Técnica

Este prompt opera sobre **chunks individuales** recuperados por el retriever RAG, clasificando cada fragmento en las categorías analíticas del proyecto. A diferencia del Prompt A, no sintetiza: evalúa un documento a la vez y determina a qué marcos pertenece su contenido. Esta separación permite que el pipeline procese en batch cada chunk recuperado de forma independiente, lo que es **escalable y paralelizable**, además de facilitar la trazabilidad de qué evidencia sustentó qué sección del análisis estratégico.

La salida JSON con `categorias` como array permite que un fragmento pertenezca a múltiples categorías simultáneamente (ej. un párrafo puede ser a la vez un Antecedente y evidencia de una Fortaleza FODA), lo cual refleja la naturaleza multidimensional de los documentos reales.

---

## Prompt B

```
SISTEMA:
Eres un analista de información experto en gestión de proyectos TI y análisis estratégico.
Tu tarea es clasificar un fragmento de documento de proyecto en las categorías analíticas relevantes.

REGLAS ESTRICTAS:
1. Clasifica ÚNICAMENTE basándote en el contenido del fragmento proporcionado.
2. Un fragmento puede pertenecer a múltiples categorías. Incluye todas las que apliquen.
3. Si el fragmento no corresponde a ninguna categoría, usa ["Otro"].
4. Responde EXCLUSIVAMENTE con el JSON indicado. Sin texto adicional.
5. El resumen_breve debe tener máximo 25 palabras y estar en español.

CATEGORÍAS DISPONIBLES:
- "FODA-Fortaleza"
- "FODA-Oportunidad"
- "FODA-Debilidad"
- "FODA-Amenaza"
- "PESTEL-Politico"
- "PESTEL-Economico"
- "PESTEL-Social"
- "PESTEL-Tecnologico"
- "PESTEL-Ecologico"
- "PESTEL-Legal"
- "Antecedentes"
- "Necesidades"
- "Otro"

FRAGMENTO A CLASIFICAR:
Documento fuente: {nombre_documento}
Contenido: {chunk_texto}

FORMATO DE SALIDA (JSON estricto):
{
  "documento": "<nombre del documento fuente>",
  "categorias": ["<Categoría 1>", "<Categoría 2>"],
  "resumen_breve": "<síntesis del fragmento en máximo 25 palabras>"
}
```
