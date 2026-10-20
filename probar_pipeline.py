"""Mini-script asíncrono: caso técnico y caso ambiguo con proveedor real."""
import asyncio
import json
import logging
from pathlib import Path
from chain import process_text


async def main():
    cases = [
        'La API en FastAPI está caída en producción. Redis devuelve timeouts y PostgreSQL agotó todas sus conexiones. Ningún usuario puede completar solicitudes.',
        'Dicen que el sistema anda raro. No se indica qué componente falla, qué tecnologías utiliza ni si hay usuarios afectados.',
    ]
    results = []
    for index, text in enumerate(cases):
        answer = await process_text(text)
        if index == 0:
            assert {v.casefold() for v in answer.tecnologias} == {'fastapi', 'redis', 'postgresql'}
            assert answer.nivel_de_criticidad.value == 'alta'
        else:
            assert answer.tecnologias == [], 'El modelo inventó tecnologías'
            assert answer.nivel_de_criticidad.value == 'media'
        results.append({'entrada': text, 'salida': answer.model_dump(mode='json'), 'resultado': 'OK'})
        print(json.dumps(results[-1], ensure_ascii=False, indent=2))
    Path(__file__).with_name('resultados-locales.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Ambos casos aprobados.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpx2').setLevel(logging.WARNING)
    try:
        asyncio.run(main())
    except Exception as error:
        print('La prueba no se completó:', type(error).__name__, '. Revisá configuración, cuota y disponibilidad del modelo.')
        raise SystemExit(1)
