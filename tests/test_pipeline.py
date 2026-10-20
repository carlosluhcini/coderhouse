import json
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
import chain
from schemas import EntidadesTecnicas

VALID = {'tecnologias': ['FastAPI'], 'nivel_de_criticidad': 'alta', 'resumen_tecnico': 'La API FastAPI está caída en producción.'}


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, replies, expected_error=False):
        requests = []

        def respond(request):
            requests.append(request)
            arguments, reason = replies[len(requests) - 1]
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call_test', 'type': 'function', 'function': {'name': 'EntidadesTecnicas', 'arguments': arguments}}]}
            return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 1, 'model': 'modelo-prueba', 'choices': [{'index': 0, 'message': message, 'finish_reason': reason}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = chain.CheckedChatOpenAI(api_key='clave-ficticia', base_url='https://example.test/v1', model='modelo-prueba', max_retries=0, http_async_client=client)
            with patch.object(chain, 'create_model', return_value=model):
                if expected_error:
                    with self.assertRaises(chain.RespuestaInvalida):
                        await chain.process_text('FastAPI está caída en producción.')
                else:
                    answer = await chain.process_text('FastAPI está caída en producción.')
                    self.assertIsInstance(answer, EntidadesTecnicas)
                    self.assertEqual(answer.tecnologias, ['FastAPI'])
        return len(requests)

    async def test_json_malformado_se_recupera(self):
        with self.assertLogs('extraccion', level='INFO') as logs:
            count = await self.exercise([('no es JSON', 'tool_calls'), (json.dumps(VALID), 'tool_calls')])
        self.assertEqual(count, 2)
        self.assertTrue(any('reintento automático' in line for line in logs.output))

    async def test_campo_faltante_se_recupera(self):
        invalid = json.dumps({'tecnologias': ['FastAPI'], 'nivel_de_criticidad': 'alta'})
        self.assertEqual(await self.exercise([(invalid, 'tool_calls'), (json.dumps(VALID), 'tool_calls')]), 2)

    async def test_truncamiento_reintenta_antes_de_validar(self):
        with patch.object(chain, 'validate_result', wraps=chain.validate_result) as validate:
            self.assertEqual(await self.exercise([('{', 'length'), (json.dumps(VALID), 'tool_calls')]), 2)
            self.assertEqual(validate.call_count, 1)

    async def test_agota_reintento_sin_devolver_datos_invalidos(self):
        self.assertEqual(await self.exercise([('invalido', 'tool_calls'), ('invalido', 'tool_calls')], expected_error=True), 2)

    async def test_rechaza_entrada_vacia_sin_llamar_al_modelo(self):
        with patch.object(chain, 'create_model') as create:
            with self.assertRaises(ValueError):
                await chain.process_text('  ')
            create.assert_not_called()

    def test_enum_y_duplicados(self):
        for changes in ({'nivel_de_criticidad': 'urgente'}, {'tecnologias': ['Redis', 'redis']}, {'tecnologias': [' ']}):
            with self.assertRaises(ValidationError):
                EntidadesTecnicas.model_validate(VALID | changes)


if __name__ == '__main__':
    unittest.main()
