"""Contrato de salida: tipos, enum y restricciones de contenido."""
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class Criticidad(str, Enum):
    baja = 'baja'
    media = 'media'
    alta = 'alta'


Tecnologia = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class EntidadesTecnicas(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    tecnologias: list[Tecnologia] = Field(max_length=30, description='Tecnologías explícitamente mencionadas; [] si no se identifica ninguna. No inventar nombres.')
    nivel_de_criticidad: Criticidad = Field(description='baja: sin fallas; media: degradación o información insuficiente; alta: caída, pérdida de datos o impacto crítico explícito')
    resumen_tecnico: str = Field(min_length=20, max_length=600, description='Resumen técnico fiel al texto; declarar incertidumbre si faltan datos')

    @field_validator('tecnologias')
    @classmethod
    def sin_duplicados(cls, values):
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError('No se admiten tecnologías duplicadas')
        return values
