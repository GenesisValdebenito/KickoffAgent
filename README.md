# AI Project Copilot 🤖💼

**AI Project Copilot** es un agente inteligente diseñado para firmas de consultoría tecnológica e ingeniería de software. Su objetivo principal es asistir en la evaluación estratégica de proyectos TI mediante el análisis automatizado de requerimientos de software y la evaluación de viabilidad financiera.

Este proyecto fue desarrollado como parte de la evaluación **"Diseño de solución con LLM y RAG"**, integrando capacidades avanzadas de Prompt Engineering, Recuperación Aumentada por Generación (RAG) y Tool Calling (Uso de herramientas).

---

## 🚀 Características Principales

1. **Análisis de Requerimientos (RAG):**
   - Capacidad de ingerir y leer documentación estructurada (Actas de reunión, Especificaciones Técnicas IEEE 830).
   - Extrae requerimientos funcionales y no funcionales, transformándolos automáticamente en formato de **Historias de Usuario**.
   - Búsqueda semántica usando base de datos vectorial local.

2. **Evaluación de Viabilidad Financiera (Tool Calling):**
   - Extrae automáticamente variables financieras clave desde actas de proyecto (Inversión inicial, Flujos de caja proyectados, Tasa de descuento).
   - Utiliza una herramienta matemática determinista (`numpy-financial`) para calcular con 100% de precisión métricas como: **VAN** (Valor Actual Neto), **TIR** (Tasa Interna de Retorno), **ROI** y **PRI**.
   - Formula una recomendación técnica formal sobre la rentabilidad de la inversión.

3. **Orquestación de Agentes con LangGraph:**
   - Toma de decisiones autónoma: El modelo LLM decide, basado en la consulta del usuario, si debe invocar la búsqueda documental (RAG) o la calculadora financiera, manteniendo el contexto de la conversación.

---

## 🏗️ Arquitectura Técnica

- **Modelo LLM Principal:** Groq (`qwen/qwen3.8-27b`) por su bajísima latencia e inferencia rápida.
- **Embeddings:** `FastEmbed` (`BAAI/bge-small-en-v1.5`), ejecutado localmente sin dependencias pesadas como PyTorch, garantizando velocidad y compatibilidad en Windows.
- **Base de Datos Vectorial:** ChromaDB (Persistente local).
- **Framework de Agentes:** LangChain / LangGraph (`create_agent`).

---

## ⚙️ Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/GenesisValdebenito/KickoffAgent.git
cd KickoffAgent
```

### 2. Instalar dependencias
Es altamente recomendado utilizar un entorno virtual (venv).
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea un archivo llamado `.env` en la raíz del proyecto y agrega tu API Key de Groq:
```env
GROQ_API_KEY=tu_clave_api_aqui
```
> **Nota:** El archivo `.env` está ignorado por git por seguridad. Nunca subas tus contraseñas al repositorio público.

### 4. Ejecutar el Agente
Para iniciar las pruebas del agente (Requerimientos IEEE 830 y Evaluación Financiera):
```bash
python agent_project_copilot.py
```

---

## 📄 Requisitos del Proyecto (Rúbrica Evaluativa)
Este repositorio cumple con los siguientes entregables de evaluación:
- [x] Formulación y justificación de prompts optimizados (`system_prompt` con reglas estrictas).
- [x] Diseño e implementación de un pipeline RAG local.
- [x] Integración de herramientas de recuperación (Tool Calling) y control de contexto conversacional (Grafo de estado).
- [x] Implementación sobre un caso de uso organizacional real (Consultoría TI).

---
*Desarrollado para el módulo de Desarrollo de Agentes Inteligentes con LLM.*
