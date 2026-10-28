"""Cliente común con streaming real, reintentos acotados y errores controlados."""
import asyncio
import importlib
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from schemas import GenerationParams, LLMConfig

logger = logging.getLogger('llm_manager')


class LLMError(Exception):
    """Error público seguro: no incluye la respuesta cruda ni credenciales."""


class AsyncLLMManager:
    def __init__(self, config: LLMConfig | None = None, *, client=None):
        self.config = config or LLMConfig.from_env()
        self.sdk = importlib.import_module(self.config.provider)
        if client is not None:
            self.client = client
        else:
            factory = self.sdk.AsyncOpenAI if self.config.provider == 'openai' else self.sdk.AsyncAnthropic
            kwargs = dict(api_key=self.config.api_key.get_secret_value(), timeout=self.config.timeout, max_retries=0)
            if self.config.base_url:
                kwargs['base_url'] = self.config.base_url
            self.client = factory(**kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.close()

    async def _stream(self, prompt: str, params: GenerationParams) -> AsyncIterator[str]:
        if self.config.provider == 'openai':
            response = await self.client.chat.completions.create(
                model=self.config.model, messages=[{'role': 'user', 'content': prompt}],
                temperature=params.temperature, max_tokens=params.max_tokens,
                top_p=params.top_p, stream=True,
            )
            async with response:
                async for chunk in response:
                    if chunk.choices:
                        choice = chunk.choices[0]
                        if choice.delta.content:
                            yield choice.delta.content
                        if choice.finish_reason == 'length':
                            raise LLMError('Respuesta incompleta: se alcanzó max_tokens.')
                        if choice.finish_reason == 'content_filter':
                            raise LLMError('El proveedor filtró la respuesta.')
        else:
            # Anthropic recomienda no combinar temperature con top_p.
            async with self.client.messages.stream(
                model=self.config.model, messages=[{'role': 'user', 'content': prompt}],
                temperature=params.temperature, max_tokens=params.max_tokens,
            ) as response:
                async for text in response.text_stream:
                    yield text
                final = await response.get_final_message()
                if final.stop_reason == 'max_tokens':
                    raise LLMError('Respuesta incompleta: se alcanzó max_tokens.')

    async def generate(self, prompt: str, params: GenerationParams | dict | None = None) -> AsyncIterator[str]:
        # La validación se ejecuta al comenzar a consumir el generador, antes de la API.
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20000:
            raise ValueError('El prompt debe contener entre 1 y 20000 caracteres.')
        params = GenerationParams.model_validate(params or {})
        if self.config.provider == 'anthropic' and (params.temperature > 1 or params.top_p != 1):
            raise ValueError('Para Anthropic, temperature debe estar entre 0 y 1 y top_p debe quedar en 1.')
        emitted = False
        try:
            async with asyncio.timeout(self.config.timeout):
                for attempt in range(self.config.retries + 1):
                    logger.info('Proveedor=%s intento=%d/%d', self.config.provider, attempt + 1, self.config.retries + 1)
                    try:
                        async with aclosing(self._stream(prompt, params)) as stream:
                            async for text in stream:
                                if text:
                                    emitted = True
                                    yield text
                        if not emitted:
                            raise LLMError('El proveedor finalizó sin enviar texto.')
                        return
                    except (self.sdk.RateLimitError, self.sdk.APIConnectionError) as error:
                        limited = isinstance(error, self.sdk.RateLimitError)
                        label = 'Límite de solicitudes o cuota (429)' if limited else 'Error de conexión o tiempo de espera'
                        if emitted or attempt >= self.config.retries:
                            suffix = ' La respuesta quedó parcial; no se repite para evitar duplicados.' if emitted else ''
                            raise LLMError(label + '.' + suffix) from None
                        delay = min(2 ** attempt, 4)
                        logger.warning('%s; reintento en %s s', label, delay)
                        await asyncio.sleep(delay)
                    except self.sdk.APIStatusError as error:
                        raise LLMError(f'El proveedor rechazó la solicitud (HTTP {error.status_code}). Revisá clave, modelo y permisos.') from None
                    except self.sdk.APIError:
                        raise LLMError('El proveedor interrumpió el stream o devolvió un evento de error.') from None
        except TimeoutError:
            raise LLMError('Se alcanzó el tiempo límite total de generación.') from None
        except asyncio.CancelledError:
            logger.info('Generación cancelada; cerrando el stream.')
            raise
