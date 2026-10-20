# Pre-entrega 3: recuperación semántica local (RAG)

RAG sobre cuatro manuales ficticios de microservicios. Usa embeddings locales multilingües, ChromaDB persistente y una cadena asíncrona LCEL con salida Pydantic. La generación usa OpenRouter o Gemini; solo la base vectorial y los embeddings son locales.

## Instalación (Python 3.12+)

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar `OPENROUTER_API_KEY` en `.env`. Se usa `openrouter/free` por defecto. Para Gemini, completar `GEMINI_API_KEY`, cambiar `LLM_PROVIDER=gemini` y `LLM_MODEL=gemini-3.8-flash`. Las variables del sistema tienen prioridad sobre `.env`. No publicar claves.

## Ejecución

```powershell
.\.venv\Scripts\python.exe ingesta.py
.\.venv\Scripts\python.exe rag.py "¿Cuál es la orden de rollback de Nube Clara?"
.\.venv\Scripts\python.exe probar_rag.py
```

La primera ingesta descarga el modelo público `intfloat/multilingual-e5-small` (ONNX; requiere internet y espacio en disco). Luego los embeddings se calculan en CPU. El generador requiere conexión y cuota del proveedor. La pregunta y hasta cuatro fragmentos se envían al proveedor seleccionado.

## Componentes

- `ingesta.py`: lee `data/`, aplica `RecursiveCharacterTextSplitter` con tamaño de 500 tokens y solapamiento de hasta 50, medidos con el tokenizer del modelo; guarda vectores, texto y referencias en `vectorstore/`.
- `embeddings.py`: usa el mismo modelo de 384 dimensiones y sus prefijos `passage:` / `query:` para indexar y consultar. El tamaño deja espacio para prefijos y tokens especiales dentro del límite de 512. Los fragmentos finales o limitados por separadores pueden ser menores que 500; nunca se agregan rellenos artificiales.
- `rag.py`: implementa `async get_rag_response(query: str)`. La cadena es recuperación → contexto y pregunta → prompt → LLM → `PydanticOutputParser`. Las operaciones locales síncronas se delegan con `asyncio.to_thread`.
- `data/`: cuatro documentos originales de ejemplo sobre la plataforma ficticia Nube Clara.
- `probar_rag.py`: pregunta documentada y pregunta trampa. Verifica respuesta, fuentes y abstención, y guarda `resultados-locales.json` (excluido de Git).

La ingesta reutiliza una colección existente sin recalcular embeddings si la huella de documentos, modelo y chunking coincide. Si cambia el corpus o la configuración, ejecutar `python ingesta.py --rebuild` con el Python del entorno. La consulta rechaza índices desactualizados o incompletos. No ejecutar reconstrucciones y consultas al mismo tiempo.

El prompt exige responder **"No lo sé"** cuando la respuesta no está en el contexto. La salida incluye `texto` y `referencias` (documento, identificador de fragmento y cita literal). Se rechazan fuentes inventadas y respuestas sin citas; esto no demuestra por sí solo que toda afirmación esté respaldada, por lo que también se prueban casos positivos y negativos. Si el proveedor falla o produce un JSON inválido, se informa un error sin fabricar una respuesta.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe probar_rag.py
```

Las pruebas unitarias no llaman al LLM. Las dos pruebas End-to-End sí usan el proveedor real: se espera la orden `nc rollback --revision estable` con referencias y, para el ganador del Mundial de 1986 (ausente del corpus), exactamente `No lo sé` sin referencias. Un fallo de formato, cuota o disponibilidad no cuenta como prueba aprobada.

Verificado el 20/10/2026 con Python 3.12.14: cuatro documentos, ocho fragmentos, reutilización del índice sin recalcular embeddings, cinco pruebas automáticas y las dos consultas End-to-End aprobadas con OpenRouter. Las versiones probadas están fijadas en `requirements.txt`; las respuestas del proveedor pueden variar en futuras ejecuciones.

`.env`, `.venv/`, `.cache/`, `vectorstore/` y los resultados locales se excluyen de Git. Cada docente puede generar el índice a partir del dataset incluido y usar su propia clave.

## Referencias

[ChromaDB](https://docs.trychroma.com/reference/python) · [LCEL asíncrono](https://reference.langchain.com/python/langchain-core/runnables/base/RunnableLambda/ainvoke) · [Text splitters](https://reference.langchain.com/python/langchain-text-splitters) · [FastEmbed](https://github.com/qdrant/fastembed)
