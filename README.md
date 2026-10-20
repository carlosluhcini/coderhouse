# Primera entrega: Orquestador concurrente de modelos

## Objetivo

Simular la lógica de un backend que consulta múltiples fuentes de IA de forma concurrente y eficiente.

## Pasos

1. **Configuración inicial:** crear un entorno con Python 3.12 o posterior.
2. **Simulación de llamadas:** definir tres corrutinas `async def` que simulen llamadas a diferentes modelos: `gpt_4_call`, `claude_3_call` y `local_llama_call`. Cada una debe usar `await asyncio.sleep()` con diferentes tiempos de espera para simular latencia de red.
3. **Orquestación:** implementar una función principal que ejecute las tres llamadas simultáneamente mediante `asyncio.gather()`.
4. **Resiliencia:** aplicar un límite global de 2 segundos mediante `asyncio.timeout()`. Si se supera, capturar la excepción y mostrar un mensaje de error sin interrumpir el programa.
5. **Control de flujo:** utilizar `asyncio.Semaphore(2)` para que, al programar 10 simulaciones de llamadas, solo 2 se ejecuten al mismo tiempo.

## Criterios de aceptación

- No utilizar `time.sleep()`, ya que bloquea la ejecución.
- Mostrar en los logs que las tareas comienzan casi al mismo tiempo.
- Manejar correctamente la excepción `TimeoutError`.
