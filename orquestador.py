"""Ejercicio: orquestador concurrente. Requiere Python 3.12 o posterior."""

import asyncio
import sys
from time import perf_counter


INICIO = perf_counter()


def log(mensaje):
    print(f"[{perf_counter() - INICIO:5.2f} s] {mensaje}", flush=True)


async def simular_modelo(nombre, demora):
    log(f"INICIO {nombre}")
    try:
        await asyncio.sleep(demora)
        log(f"FIN {nombre}")
        return f"Respuesta simulada de {nombre}"
    except asyncio.CancelledError:
        log(f"CANCELADA {nombre}")
        raise  # Permite que asyncio.timeout complete la cancelación.


async def gpt_4_call(demora=0.3):
    return await simular_modelo("GPT-4", demora)


async def claude_3_call(demora=0.5):
    return await simular_modelo("Claude 3", demora)


async def local_llama_call(demora=0.7):
    return await simular_modelo("Llama local", demora)


async def consultar_modelos(demora_llama=0.7):
    try:
        # El límite abarca el conjunto completo de llamadas.
        async with asyncio.timeout(2):
            resultados = await asyncio.gather(
                gpt_4_call(),
                claude_3_call(),
                local_llama_call(demora_llama),
            )
        for resultado in resultados:
            log(resultado)
        return resultados
    except TimeoutError:
        # Se captura fuera del contexto: allí se transforma la cancelación
        # en TimeoutError. El programa puede continuar con la siguiente prueba.
        log("ERROR: se superó el límite total de 2 segundos.")
        return None


async def probar_semaforo():
    semaforo = asyncio.Semaphore(2)
    activas = 0
    maximo_observado = 0

    async def llamada_limitada(numero):
        nonlocal activas, maximo_observado
        async with semaforo:
            activas += 1
            maximo_observado = max(maximo_observado, activas)
            log(f"INICIO simulación {numero:02d} | activas: {activas}")
            try:
                await asyncio.sleep(0.25)
                return f"Resultado {numero}"
            finally:
                activas -= 1
                log(f"FIN simulación {numero:02d} | activas: {activas}")

    # Las diez se programan juntas; el semáforo admite dos a la vez.
    async with asyncio.timeout(2):
        resultados = await asyncio.gather(
            *(llamada_limitada(numero) for numero in range(1, 11))
        )
    log(f"Completadas: {len(resultados)} | máximo simultáneo: {maximo_observado}")
    assert len(resultados) == 10
    assert maximo_observado == 2


async def main():
    if sys.version_info < (3, 12):
        raise RuntimeError("Este ejercicio requiere Python 3.12 o posterior.")

    log("PRUEBA 1: tres modelos concurrentes; todos responden a tiempo.")
    resultados = await consultar_modelos()
    assert resultados is not None and len(resultados) == 3

    log("PRUEBA 2: Llama demora 3 segundos; debe ocurrir TimeoutError.")
    assert await consultar_modelos(demora_llama=3) is None

    log("El programa sigue funcionando después del error.")
    log("PRUEBA 3: diez llamadas con un máximo de dos simultáneas.")
    try:
        await probar_semaforo()
    except TimeoutError:
        log("ERROR: las diez simulaciones superaron el límite total de 2 segundos.")
    log("Programa finalizado.")


if __name__ == "__main__":
    asyncio.run(main())
