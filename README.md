# Orquestador concurrente de modelos

Proyecto de Python que simula un backend de consultas a modelos de IA. No requiere claves de API ni dependencias externas.

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
