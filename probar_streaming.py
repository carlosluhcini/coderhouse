"""Ejecutar: python probar_streaming.py --timestamps"""
import argparse
import asyncio
import logging
from contextlib import aclosing
from time import perf_counter
from pydantic import ValidationError
from manager import AsyncLLMManager, LLMError
from schemas import GenerationParams


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', default='Explicá en español qué es asyncio, en cuatro frases breves.')
    parser.add_argument('--temperature', type=float, default=0.7)
    parser.add_argument('--max-tokens', type=int, default=512)
    parser.add_argument('--timestamps', action='store_true', help='Mostrar cada fragmento con su tiempo de llegada')
    args = parser.parse_args()
    try:
        params = GenerationParams(temperature=args.temperature, max_tokens=args.max_tokens)
        async with AsyncLLMManager() as manager:
            start, count = perf_counter(), 0
            async with aclosing(manager.generate(args.prompt, params)) as stream:
                async for text in stream:
                    count += 1
                    if args.timestamps:
                        print(f'[{perf_counter() - start:6.2f} s] {text!r}', flush=True)
                    else:
                        print(text, end='', flush=True)
            print(f'\nFin: {count} fragmentos en {perf_counter() - start:.2f} s.')
        return 0
    except ValidationError:
        print('Configuración inválida. Revisá proveedor, modelo, clave y rangos de parámetros.')
    except (LLMError, ValueError) as error:
        print('\nError controlado:', error)
    return 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpx2').setLevel(logging.WARNING)
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print('\nGeneración cancelada por el usuario.')
