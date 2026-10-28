import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
import openai
import anthropic
from pydantic import ValidationError
from schemas import GenerationParams, LLMConfig
from manager import AsyncLLMManager, LLMError


def config(provider='openai', **kwargs):
    return LLMConfig(provider=provider, model='modelo-prueba', api_key='clave-ficticia', timeout=5, retries=1, **kwargs)


class SSE(httpx.AsyncByteStream):
    def __init__(self, packets, fail_after=False):
        self.packets, self.sent, self.closed, self.fail_after = packets, 0, False, fail_after

    async def __aiter__(self):
        for packet in self.packets:
            self.sent += 1
            yield packet.encode()
        if self.fail_after:
            raise httpx.ReadError('corte simulado')

    async def aclose(self):
        self.closed = True


def openai_packet(text, reason=None):
    data = {'id': 'test', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'test', 'choices': [{'index': 0, 'delta': {'content': text}, 'finish_reason': reason}]}
    return 'data: ' + json.dumps(data) + '\n\n'


def anthropic_packets():
    events = [
        ('message_start', {'message': {'id': 'test', 'type': 'message', 'role': 'assistant', 'model': 'test', 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 1, 'output_tokens': 0}}}),
        ('content_block_start', {'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
        ('content_block_delta', {'index': 0, 'delta': {'type': 'text_delta', 'text': 'Hola'}}),
        ('content_block_delta', {'index': 0, 'delta': {'type': 'text_delta', 'text': ' mundo'}}),
        ('content_block_stop', {'index': 0}),
        ('message_delta', {'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 2}}),
        ('message_stop', {}),
    ]
    return ['event: ' + name + '\ndata: ' + json.dumps({'type': name, **data}) + '\n\n' for name, data in events]


class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def use(self, provider, handler, callback):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            cls = openai.AsyncOpenAI if provider == 'openai' else anthropic.AsyncAnthropic
            client = cls(api_key='clave-ficticia', base_url='https://example.test/v1', http_client=http, max_retries=0)
            async with AsyncLLMManager(config(provider), client=client) as manager:
                return await callback(manager)

    async def test_openai_entrega_antes_de_consumir_todo(self):
        stream = SSE([openai_packet('Hola'), openai_packet(' mundo'), openai_packet('', 'stop'), 'data: [DONE]\n\n'])
        async def check(manager):
            generator = manager.generate('Saludá')
            self.assertEqual(await anext(generator), 'Hola')
            self.assertEqual(stream.sent, 1)
            self.assertEqual(''.join([t async for t in generator]), ' mundo')
        await self.use('openai', lambda r: httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=stream), check)
        self.assertTrue(stream.closed)

    async def test_anthropic_stream(self):
        stream = SSE(anthropic_packets())
        async def check(manager):
            self.assertEqual(''.join([t async for t in manager.generate('Saludá')]), 'Hola mundo')
        await self.use('anthropic', lambda r: httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=stream), check)
        self.assertTrue(stream.closed)

    async def test_429_y_red_reintentan_antes_de_emitir(self):
        for provider in ('openai', 'anthropic'):
            for failure in ('429', 'network'):
                with self.subTest(provider=provider, failure=failure):
                    calls = []
                    def handler(request):
                        calls.append(request)
                        if len(calls) == 1:
                            if failure == 'network':
                                raise httpx.ConnectError('red simulada', request=request)
                            return httpx.Response(429, json={'error': {'type': 'rate_limit_error', 'message': 'no imprimir secreto'}})
                        packets = [openai_packet('OK'), openai_packet('', 'stop'), 'data: [DONE]\n\n'] if provider == 'openai' else anthropic_packets()
                        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=SSE(packets))
                    async def check(manager):
                        self.assertTrue(''.join([t async for t in manager.generate('Hola')]))
                    with patch('manager.asyncio.sleep', return_value=None):
                        await self.use(provider, handler, check)
                    self.assertEqual(len(calls), 2)

    async def test_429_persistente_error_controlado(self):
        async def check(manager):
            with self.assertRaisesRegex(LLMError, '429') as error:
                _ = [t async for t in manager.generate('Hola')]
            self.assertNotIn('secreto', str(error.exception))
        with patch('manager.asyncio.sleep', return_value=None):
            await self.use('openai', lambda r: httpx.Response(429, json={'error': {'message': 'secreto'}}), check)

    async def test_error_despues_de_texto_no_repite(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=SSE([openai_packet('Parcial')], fail_after=True))
        async def check(manager):
            generator = manager.generate('Hola')
            self.assertEqual(await anext(generator), 'Parcial')
            with self.assertRaisesRegex(LLMError, 'parcial|interrumpió'):
                await anext(generator)
        await self.use('openai', handler, check)
        self.assertEqual(len(calls), 1)

    async def test_validacion_no_llama_api(self):
        def handler(request):
            self.fail('No debe llamar a la API')
        async def check(manager):
            with self.assertRaises(ValidationError):
                _ = [t async for t in manager.generate('Hola', {'temperature': 3})]
        await self.use('openai', handler, check)

    async def test_401_controlado_sin_exponer_respuesta(self):
        async def check(manager):
            with self.assertRaisesRegex(LLMError, 'HTTP 401') as error:
                _ = [t async for t in manager.generate('Hola')]
            self.assertNotIn('clave-expuesta', str(error.exception))
        await self.use('openai', lambda r: httpx.Response(401, json={'error': {'message': 'clave-expuesta'}}), check)

    async def test_cancelacion_cierra_stream(self):
        started = asyncio.Event()
        class BlockingSSE(SSE):
            async def __aiter__(self):
                started.set()
                await asyncio.Event().wait()
                yield b''
        stream = BlockingSSE([])
        async def check(manager):
            async def consume():
                return [t async for t in manager.generate('Hola')]
            task = asyncio.create_task(consume())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        await self.use('openai', lambda r: httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=stream), check)
        self.assertTrue(stream.closed)

    async def test_cerrar_generador_libera_stream(self):
        stream = SSE([openai_packet('Hola'), openai_packet(' mundo')])
        async def check(manager):
            generator = manager.generate('Hola')
            await anext(generator)
            await generator.aclose()
        await self.use('openai', lambda r: httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=stream), check)
        self.assertTrue(stream.closed)

    def test_limites_parametros(self):
        for values in ({'temperature': -0.1}, {'temperature': 2.1}, {'max_tokens': 0}, {'max_tokens': 1.5}, {'top_p': 2}, {'temperature': float('nan')}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                GenerationParams(**values)
        self.assertEqual(GenerationParams(temperature=2, max_tokens=1).max_tokens, 1)


if __name__ == '__main__':
    unittest.main()
