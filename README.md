# Primera entrega: Orquestador concurrente de modelos

En este ejercicio, simularás la lógica de un backend que debe consultar múltiples fuentes de IA de forma eficiente.

Pasos:

Configuración Inicial: Crea un entorno con Python 3.12+.
Simulación de Llamadas: Define tres corrutinas async def que simulen llamadas a diferentes modelos (por ejemplo, gpt_4_call, claude_3_call, local_llama_call). Cada una debe usar await asyncio.sleep() con diferentes tiempos de espera para simular latencia de red.
Orquestación: Implementa una función principal que dispare las tres llamadas simultáneamente usando asyncio.gather.
Resiliencia: Añade un asyncio.timeout de 2 segundos a la ejecución total. Si alguna llamada tarda más, el programa debe capturar la excepción y mostrar un mensaje de error sin detenerse.
Control de Flujo: Utiliza un asyncio.Semaphore para asegurar que, aunque intentes disparar 10 simulaciones de llamadas, solo 2 se ejecuten al mismo tiempo.
Criterios de Aceptación:

El código no debe usar time.sleep (bloqueante).
Se debe observar en los logs que las tareas inician casi al mismo tiempo.
Se debe manejar correctamente la excepción TimeoutError.
