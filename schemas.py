"""Contrato validado antes de enviar parámetros a una API."""
import os
from pathlib import Path
from typing import Annotated, Literal
from annotated_types import Ge, Le
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class GenerationParams(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, hide_input_in_errors=True)
    temperature: Annotated[float, Ge(0), Le(2)] = Field(default=0.7, description='Temperatura entre 0 y 2')
    max_tokens: Annotated[int, Ge(1), Le(16384)] = Field(default=512, strict=True)
    top_p: Annotated[float, Ge(0), Le(1)] = Field(default=1.0)


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, hide_input_in_errors=True)
    provider: Literal['openai', 'anthropic']
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr = Field(exclude=True, repr=False)
    base_url: str | None = None
    timeout: float = Field(default=90, gt=0, le=300)
    retries: int = Field(default=1, ge=0, le=3)

    @field_validator('model')
    @classmethod
    def nonblank_model(cls, value):
        if not value.strip():
            raise ValueError('LLM_MODEL no puede estar vacío')
        return value.strip()

    @field_validator('api_key')
    @classmethod
    def nonblank_key(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError('Falta configurar la clave del proveedor')
        return value

    @classmethod
    def from_env(cls, path: Path | None = None):
        load_dotenv(path or Path(__file__).with_name('.env'), override=False)
        provider = os.getenv('LLM_PROVIDER', 'openai').strip().lower()
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').strip()
        key = os.getenv('ANTHROPIC_API_KEY', '') if provider == 'anthropic' else os.getenv('OPENAI_API_KEY', '')
        # La clave de OpenRouter se usa solo contra su endpoint explícito.
        if provider == 'openai' and base_url.rstrip('/') == 'https://openrouter.ai/api/v1':
            key = os.getenv('OPENROUTER_API_KEY') or key
        if provider == 'openai' and base_url.rstrip('/') == 'https://generativelanguage.googleapis.com/v1beta/openai':
            key = os.getenv('GEMINI_API_KEY') or key
        return cls(provider=provider, model=os.getenv('LLM_MODEL', ''), api_key=key,
                   base_url=base_url if provider == 'openai' else None,
                   timeout=os.getenv('LLM_TIMEOUT', '90'), retries=os.getenv('LLM_RETRIES', '1'))
