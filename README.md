# Primera entrega: Orquestador concurrente de modelos

Simulación de consultas a tres modelos de IA con `asyncio.gather()`, un límite de 2 segundos y un semáforo que permite hasta 2 llamadas simultáneas.

## Requisitos

Python 3.12 o posterior. No requiere dependencias externas ni claves de API.

## Ejecución

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe orquestador.py
```

Se ejecutan tres pruebas: llamadas concurrentes, manejo de `TimeoutError` y diez simulaciones con un máximo de dos activas. Los resultados se muestran en la consola.
