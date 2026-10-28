# Pre-entrega 1: AsyncLLMManager y streaming

Implementación corregida de la entrega: selección de OpenAI o Anthropic por configuración, generación asíncrona por fragmentos, parámetros Pydantic y manejo controlado de errores. El orquestador de simulaciones anterior se conserva en la rama `primera-entrega`.

## Instalación (Python 3.12+)

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Completar `.env` con `LLM_PROVIDER=openai` o `anthropic`, `LLM_MODEL` y la clave correspondiente (`OPENAI_API_KEY` o `ANTHROPIC_API_KEY`). Elegir un modelo habilitado que admita los parámetros de generación. No subir `.env`.

```powershell
.\.venv\Scripts\python.exe probar_streaming.py --timestamps
```

Sin `--timestamps`, los fragmentos se imprimen juntos a medida que llegan, con `flush=True`. Con esa opción, cada fragmento incluye su tiempo de llegada. No se agrega latencia artificial ni se espera la respuesta completa antes de imprimir.

## Variables y parámetros

| Variable | Uso |
| --- | --- |
| `LLM_PROVIDER` | `openai` o `anthropic`; selecciona el SDK y el cliente asíncrono. |
| `LLM_MODEL` | ID del modelo, obligatorio. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Clave del proveedor seleccionado. |
| `OPENAI_BASE_URL` | Endpoint opcional compatible; predeterminado: API de OpenAI. |
| `OPENROUTER_API_KEY` | Alternativa usada solo si el endpoint configurado es OpenRouter. |
| `GEMINI_API_KEY` | Alternativa usada solo si el endpoint configurado es el compatible de Gemini. |
| `LLM_TIMEOUT` | Límite global en segundos, de 0 a 300 (sin incluir 0); predeterminado: 90. |
| `LLM_RETRIES` | Reintentos antes de emitir texto, de 0 a 3; predeterminado: 1. |

`schemas.py` valida con Pydantic, `Field`, `Ge` y `Le`: temperatura 0-2, `max_tokens` entero 1-16384 y `top_p` 0-1. Anthropic tiene una restricción adicional de temperatura 0-1 y no se combina con `top_p` configurable. Los límites efectivos también dependen del modelo; un rechazo del proveedor se informa de forma controlada.

`manager.py` implementa `AsyncLLMManager.generate()` como generador asíncrono con `yield`. Consume la respuesta con `async for`, cierra clientes y streams, propaga la cancelación y captura `RateLimitError`, `APIConnectionError`, tiempos de espera y errores de API. Reintenta red/429 con espera asíncrona solo antes del primer fragmento; después informa una respuesta parcial sin repetirla. Los errores se exponen como `LLMError`, separados del texto generado.

## Probar con OpenRouter

Se puede usar el SDK OpenAI contra OpenRouter sin afirmar que sea una prueba directa de OpenAI:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=openrouter/free
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=tu_clave_local
```

```powershell
.\.venv\Scripts\python.exe probar_streaming.py --timestamps --max-tokens 1024
```

## Pruebas sin consumir API

También puede probarse el SDK OpenAI con Gemini configurando `LLM_PROVIDER=openai`, `LLM_MODEL=gemini-3.8-flash`, `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/` y `GEMINI_API_KEY`. Esto selecciona el SDK OpenAI, no el servicio de OpenAI.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan los SDK reales con transporte HTTP simulado: selección de proveedor, fragmentos SSE de ambos servicios, parámetros inválidos antes de la llamada, red, 429, reintentos, cancelación y corte después de emitir texto. Las claves ficticias nunca se envían a servicios externos. El script de streaming sí requiere una clave real y cuota del proveedor.

Verificación del 28/10/2026: streaming real con el SDK OpenAI contra el endpoint compatible de Gemini, con cuatro fragmentos recibidos en tiempos distintos. OpenAI y Anthropic directos se verifican con transporte simulado, sin claves reales de esas cuentas. Un 401 real de OpenRouter produjo un mensaje controlado. Las pruebas de red y 429 son simuladas para reproducir el fallo sin provocar límites del servicio.

Referencias: [OpenAI Python SDK](https://developers.openai.com/api/reference/python) y [streaming de Anthropic](https://platform.claude.com/docs/en/build-with-claude/streaming).
