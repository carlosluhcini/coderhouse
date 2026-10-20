"""Dos pruebas E2E reales: respuesta sustentada y abstención sin contexto."""
import asyncio
import json
from config import ROOT
from rag import get_rag_response


async def main():
    cases = [
        ('¿Cuál es la orden de rollback de Nube Clara?', 'nc rollback --revision estable'),
        ('¿Quién ganó la Copa Mundial de fútbol de 1986?', None),
    ]
    results = []
    for question, expected in cases:
        answer = await get_rag_response(question)
        if expected is None:
            assert answer.texto == 'No lo sé' and not answer.referencias, 'El modelo no se abstuvo en la pregunta trampa'
        else:
            assert expected in answer.texto and answer.referencias, 'Falta la orden documentada o sus referencias'
        results.append({'pregunta': question, 'respuesta': answer.model_dump(), 'resultado': 'OK'})
        print(json.dumps(results[-1], ensure_ascii=False, indent=2))
    (ROOT / 'resultados-locales.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Dos pruebas reales aprobadas. Resultados guardados localmente.')


if __name__ == '__main__':
    asyncio.run(main())
