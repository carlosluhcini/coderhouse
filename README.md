# Primera entrega: Orquestador concurrente de modelos

**Autor:** Carlos Luchini  
**Curso:** Coderhouse

Simulación en Python de un backend que consulta tres modelos de IA de forma concurrente, maneja un tiempo límite global y limita la cantidad de llamadas simultáneas.

## Requisitos

- Python 3.12 o posterior (verificado con Python 3.12.14).
- Solo se utiliza la biblioteca estándar de Python.
- No requiere claves de API, cuentas externas ni instalación de dependencias.

## Ejecutar en Windows

Abrir PowerShell en la carpeta del proyecto y ejecutar:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe orquestador.py
```

Si el entorno ya existe, ejecutar solamente la segunda línea.

## Ejecutar en macOS o Linux

```sh
python3 -m venv .venv
.venv/bin/python orquestador.py
```

## Archivos de la entrega

```text
README.md          Instrucciones y explicación del ejercicio
orquestador.py     Implementación y demostraciones ejecutables
pyproject.toml     Datos del proyecto y versión requerida de Python
.gitignore         Exclusión del entorno virtual y archivos locales
```

## Desarrollo de la consigna

| Paso | Implementación |
| --- | --- |
| 1. Python 3.12+ | Entorno virtual y requisito declarado en `pyproject.toml`. |
| 2. Tres corrutinas | `gpt_4_call`, `claude_3_call` y `local_llama_call`, cada una con `await asyncio.sleep()` y una latencia diferente: 0,3, 0,5 y 0,7 segundos. |
| 3. Orquestación | `main()` ejecuta las demostraciones y `consultar_modelos()` programa las tres consultas con `asyncio.gather()`. |
| 4. Resiliencia | `asyncio.timeout(2)` limita el grupo completo de llamadas. `except TimeoutError` muestra el error y permite continuar. |
| 5. Control de flujo | `probar_semaforo()` programa diez simulaciones con `asyncio.gather()` y `asyncio.Semaphore(2)` admite como máximo dos simultáneamente. |

## Pruebas y resultados esperados

El programa ejecuta tres demostraciones consecutivas:

1. **Concurrencia:** los tres modelos muestran INICIO prácticamente en el mismo instante. El grupo termina en aproximadamente 0,7 segundos, en lugar de sumar las tres esperas.
2. **Tiempo límite:** Llama intenta demorar 3 segundos. A los 2 segundos del inicio de ese grupo se cancela la llamada pendiente, se captura `TimeoutError` y se muestra un mensaje de error. Luego el programa continúa con la tercera demostración.
3. **Semáforo:** se programan diez llamadas con esperas de 0,25 segundos. Se completan en cinco tandas, en aproximadamente 1,25 segundos. Los logs muestran las tareas activas y el máximo observado es 2.

Ejemplo abreviado de salida:

```text
[ 0.00 s] INICIO GPT-4
[ 0.00 s] INICIO Claude 3
[ 0.00 s] INICIO Llama local
...
ERROR: se superó el límite total de 2 segundos.
El programa sigue funcionando después del error.
...
Completadas: 10 | máximo simultáneo: 2
Programa finalizado.
```

Los tiempos son aproximados. Cada grupo tiene un límite global de 2 segundos, incluyendo la espera del semáforo. La ejecución completa dura alrededor de 4 segundos porque las tres demostraciones se ejecutan una después de otra.

## Criterios de aceptación

- Las esperas usan `await asyncio.sleep()`; no se usa `time.sleep()`.
- Los logs incluyen marcas de tiempo que permiten comprobar el inicio concurrente.
- `TimeoutError` se captura fuera de `asyncio.timeout()` y no interrumpe las demostraciones siguientes.
- Las comprobaciones del programa verifican tres respuestas, el caso de tiempo límite y diez resultados con un máximo de dos llamadas simultáneas.
