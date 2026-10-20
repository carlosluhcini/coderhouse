# Pre-entrega 2: Pipeline de procesamiento validado

Extracción de tecnologías, criticidad y resumen técnico mediante LangChain LCEL y Pydantic. Incluye ejecución asíncrona, validación y un reintento automático ante salida mal formada, incompleta o truncada.

## Ejecutar (Python 3.12+)

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `OPENROUTER_API_KEY` en `.env` y ejecutar:

```powershell
.\.venv\Scripts\python.exe probar_pipeline.py
```

La configuración predeterminada usa OpenRouter y `openrouter/free`. Para Gemini, configurar `GEMINI_API_KEY`, `LLM_PROVIDER=gemini` y `LLM_MODEL=gemini-3.8-flash`. El modelo debe admitir llamadas a herramientas. Las variables del sistema tienen prioridad sobre `.env`. La consulta se envía al proveedor seleccionado y está sujeta a su cuota y disponibilidad.

## Componentes

- `schemas.py`: campos obligatorios, enum `baja/media/alta`, nombres de tecnologías no vacíos ni duplicados y resumen de 20 a 600 caracteres. Una lista vacía es válida cuando el texto no identifica tecnologías; así no se obliga al modelo a inventarlas.
- `chain.py`: `ChatPromptTemplate` con variables `text` y `format_instructions`; cadena `prompt | model.with_structured_output(EntidadesTecnicas, ...) | validación`.
- `process_text(text)`: usa `.ainvoke()` y devuelve una instancia Pydantic. La cadena completa tiene `.with_retry(stop_after_attempt=2)`: un intento inicial y un reintento. No se reintentan errores de claves o configuración.
- `probar_pipeline.py`: ejecuta de forma asíncrona un incidente crítico y un texto ambiguo, con comprobaciones y logs de validación e intentos. No registra claves ni respuestas crudas.

Se usa `include_raw=True` para distinguir errores de parseo de objetos válidos. El cliente comprueba `finish_reason` antes del parser estructurado y rechaza `length`, `max_tokens` y `content_filter`. Si el reintento también falla, el error se propaga: nunca se devuelve un objeto inválido ni una respuesta de reemplazo inventada. Un truncamiento persistente requiere revisar el presupuesto de tokens.

## Ejemplo de salida

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "La API está caída en producción; Redis presenta timeouts y PostgreSQL agotó sus conexiones."
}
```

En el caso ambiguo se espera `tecnologias: []`, criticidad `media` y un resumen que reconozca la falta de datos. El esquema valida la estructura; las comprobaciones de los ejemplos también revisan el contenido esperado.

## Pruebas sin consumir API

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas simulan respuestas HTTP: JSON inválido, campos faltantes, truncamiento, recuperación y agotamiento de reintentos. No requieren claves. El mini-script usa el proveedor real; guarda sus resultados en `resultados-locales.json`, excluido de Git junto con `.env` y `.venv/`.

Verificado el 20/10/2026 con Python 3.12.14: seis pruebas automáticas aprobadas y ambos casos reales aprobados con OpenRouter. Las versiones probadas están fijadas en `requirements.txt`.

Referencias: [salida estructurada](https://reference.langchain.com/python/langchain-openai/chat_models/base/BaseChatOpenAI/with_structured_output) y [reintentos](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/with_retry).
