# Orquestador concurrente de modelos

Proyecto de Python que simula un backend de consultas a modelos de IA. El modo predeterminado no requiere claves de API ni dependencias externas. Opcionalmente permite consultar OpenRouter y Gemini con claves propias.

## Requisitos

Python 3.12 o posterior.

## Ejecutar en Windows

Desde esta carpeta, crear el entorno y ejecutar en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe orquestador.py
```

Verificado con Python 3.12.14. El entorno `.venv` se crea localmente y no se incluye en Git.

En macOS o Linux:

```sh
python3 -m venv .venv
.venv/bin/python orquestador.py
```

## Archivos del proyecto

- `orquestador.py`: corrutinas, orquestación y tres demostraciones ejecutables.
- `pyproject.toml`: información del proyecto y versión requerida de Python.
- `.gitignore`: excluye el entorno local y archivos temporales del control de versiones.

## Funcionamiento

1. **Concurrencia:** `gpt_4_call`, `claude_3_call` y `local_llama_call` esperan 0,3, 0,5 y 0,7 segundos usando `await asyncio.sleep()`. `asyncio.gather()` las programa juntas. Los logs muestran sus inicios prácticamente en el mismo instante.
2. **Resiliencia:** una segunda consulta hace que Llama intente tardar 3 segundos. `asyncio.timeout(2)` limita el grupo completo, cancela la llamada pendiente y genera `TimeoutError`. El error se captura fuera del contexto y el programa continúa. No se devuelven resultados parciales en esta demostración.
3. **Control de flujo:** se programan diez simulaciones y `asyncio.Semaphore(2)` permite ejecutar solo dos a la vez. Cada simulación espera 0,25 segundos. Las cinco tandas completan aproximadamente en 1,25 segundos, con un límite global de 2 segundos.

El registro incluye el tiempo transcurrido, el inicio y fin de cada llamada y el contador de tareas activas. El script comprueba mediante aserciones que obtiene tres respuestas en la primera prueba, que maneja el tiempo límite en la segunda y que completa diez simulaciones con un máximo de dos simultáneas en la tercera.

## Resultado esperado

La ejecución completa demora unos 4 segundos. Debe mostrar un error de tiempo límite durante la segunda prueba y luego continuar hasta:

```text
Completadas: 10 | máximo simultáneo: 2
Programa finalizado.
```

Los tiempos pueden variar ligeramente según el equipo. Todas las esperas son asíncronas.

El tiempo límite de 2 segundos se aplica a cada ejecución del grupo de llamadas, incluyendo la espera por el semáforo. El programa completo dura más porque ejecuta tres demostraciones consecutivas, cada una con su propio límite.

## Cumplimiento de la consigna

| Requisito | Implementación |
| --- | --- |
| Python 3.12+ | Entorno verificado con Python 3.12.14 y requisito en `pyproject.toml`. |
| Tres corrutinas con diferentes latencias | `gpt_4_call`, `claude_3_call` y `local_llama_call` usan cada una `await asyncio.sleep()`. |
| Consultas simultáneas | `consultar_modelos` usa `asyncio.gather()`. |
| Límite global de 2 segundos | `asyncio.timeout(2)` abarca el grupo completo. |
| Manejo del error y continuidad | `except TimeoutError` muestra un mensaje; luego se ejecuta la prueba del semáforo. |
| Diez llamadas con máximo dos activas | `probar_semaforo` usa `asyncio.Semaphore(2)` y registra el máximo observado. |
| Sin esperas bloqueantes | Las esperas simuladas usan exclusivamente `asyncio.sleep()`. |
| Inicio casi simultáneo visible | Los logs incluyen marcas de tiempo desde el inicio. |

## Pruebas opcionales con APIs reales

Instalar las dependencias adicionales:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-real.txt
```

Copiar `.env.example` como `.env` si todavía no existe y completar las claves en ese archivo local:

```dotenv
OPENROUTER_API_KEY=tu_clave_de_openrouter
GEMINI_API_KEY=tu_clave_de_gemini
OPENROUTER_MODEL=openrouter/free
GEMINI_MODEL=gemini-3.8-flash
```

`.env` está excluido de Git; `.env.example` contiene solamente nombres de variables y modelos. Las variables de entorno del sistema tienen prioridad sobre `.env`.

Ejecutar una consulta a cada proveedor en paralelo:

```powershell
.\.venv\Scripts\python.exe orquestador.py --real
```

El límite global predeterminado sigue siendo de 2 segundos. Para dar más tiempo a los proveedores durante una prueba manual:

```powershell
.\.venv\Scripts\python.exe orquestador.py --real --timeout 30 --prompt "Explicá asyncio en una oración."
```

El modo real usa un semáforo de dos permisos y consultas HTTP asíncronas. Realiza dos consultas, una por proveedor; las tres corrutinas y las diez simulaciones exigidas por el ejercicio se ejecutan en el modo predeterminado. Si un proveedor falla, se muestra el motivo general y el otro puede terminar. El límite global cancela las consultas pendientes. El modo real devuelve un código de salida 1 cuando hay errores, sin mostrar trazas ni claves.

OpenRouter usa por defecto su [router de modelos gratuitos](https://openrouter.ai/collections/free-models). Gemini usa el modelo del [ejemplo oficial de inicio](https://ai.google.dev/gemini-api/docs/generate-content/get-started). Se pueden cambiar los modelos en `.env`; su disponibilidad, cuotas y facturación dependen de cada cuenta. La prueba real envía el prompt a ambos servicios.

## Verificación sin consumir API

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas de las integraciones usan respuestas HTTP simuladas y no necesitan claves reales.
