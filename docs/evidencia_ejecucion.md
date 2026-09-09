# Evidencia de Ejecución del Sistema — KickoffAgent

Este documento complementa los diagramas de arquitectura ([`01_arquitectura_kickoffagent.drawio`](file:///c:/Users/Usuario/Desktop/School/ISIA-VR/KickoffAgent/docs/01_arquitectura_kickoffagent.drawio)) y flujo ([`02_flujo_kickoffagent.drawio`](file:///c:/Users/Usuario/Desktop/School/ISIA-VR/KickoffAgent/docs/02_flujo_kickoffagent.drawio)) registrando formalmente los resultados empíricos obtenidos en las pruebas de validación agéntica.

---

## 1. Resumen del TEST 1 — Consulta RAG (IEEE 830)

- **Consulta evaluada:**
  > *"¿Cuáles son los requerimientos funcionales aprobados y en qué documento se basan?"*

- **Flujo ejecutado en la arquitectura:**
  1. El orquestador agéntico en `src/kickoff_agent.py` analizó la consulta e invocó la herramienta `consultar_documentacion_proyecto`.
  2. El retriever semántico recuperó los fragmentos más relevantes ($k=3$) desde la colección `kickoff_agent_knowledge` en ChromaDB (vectorizados con FastEmbed `BAAI/bge-small-en-v1.5`).
  3. El modelo estructuró formalmente la respuesta:
     - **RF-01 (Autenticación OAuth2):** Desglosado en formato Historia de Usuario (*Como / Quiero / Para*).
     - **RF-02 (Reportes exportables PDF/Excel < 3 segundos).**
     - **RNF-01 (Disponibilidad 99.9% en horario hábil).**
  4. **Trazabilidad y Auditoría:** Se incluyó obligatoriamente la cita formal a la fuente `[Especificacion_IEEE830.pdf]` y contextualización con `[Acta_Reunion_01.pdf]`.
- **Dictamen:** ✅ **Exitoso — Grounding estricto sin alucinaciones.**

---

## 2. Resumen del TEST 2 — Evaluación Financiera Automatizada (Tool Calling)

- **Consulta evaluada:**
  > *"Revisa los documentos del proyecto, busca los datos de inversión y evalúa si es viable financieramente."*

- **Flujo ejecutado en la arquitectura:**
  1. El LLM extrajo del acta de reunión los parámetros de negocio:
     - Inversión inicial ($I_0$): `$12.000.000 CLP`
     - Flujos proyectados a 3 años: `$4.500.000 CLP`, `$5.000.000 CLP`, `$6.200.000 CLP`
     - Tasa de descuento corporativa: `10%`
  2. En lugar de calcular probabilísticamente, el agente invocó la herramienta determinista `calcular_metricas_financieras` basada en `numpy-financial` con validación estricta Pydantic (`FinancialEvalInput`).
  3. El agente devolvió la tabla comparativa formal con la recomendación técnica fundamentada.

### Tabla de Métricas Financieras Certificadas

| Métrica | Resultado Calculado (`numpy-financial`) | Criterio de Decisión | Estado |
|---|---|---|---|
| **Inversión Inicial** | **$12.000.000 CLP** | Presupuesto límite del acta de reunión | Base de Inversión |
| **VAN (NPV)** | **+$881.292,26 CLP** | VAN > 0 (Crea valor económico) | ✅ Positivo / Aprobado |
| **TIR (IRR)** | **13,9%** | TIR (13,9%) > Tasa Descuento (10,0%) | ✅ Supera umbral exigido (+3,9%) |
| **ROI** | **30,83%** | ROI > 0 (Rentabilidad positiva sobre capital) | ✅ Rentable |
| **PRI (Recuperación)** | **3 periodos (años)** | PRI ≤ horizonte proyectado (3 años) | ✅ Recuperación al cierre del año 3 |
| **Dictamen Técnico Formal** | **PROYECTO FINANCIERAMENTE VIABLE** | Cumplimiento conjunto de criterios VAN y TIR | ✅ **APROBADO** |

- **Dictamen:** ✅ **Exitoso — 100% determinismo matemático.**

---

## 3. Reproducción de las Pruebas

Para replicar la ejecución en el entorno local:

```bash
python src/kickoff_agent.py
```
