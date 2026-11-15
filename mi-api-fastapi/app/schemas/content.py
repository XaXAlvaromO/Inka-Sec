from typing import Literal
from pydantic import BaseModel, Field

class CombItem(BaseModel):
    dimension: Literal["capacidad", "oportunidad", "motivacion"]
    code: str = Field(min_length=1, max_length=30)
    value: int = Field(ge=1, le=5)

class CapacityAnswer(BaseModel):
    index: int = Field(ge=0, le=19, description="Número de la pregunta en el módulo")
    choice: int = Field(ge=0, le=19, description="Número de la opción elegida")

class CapacityPayload(BaseModel):
    answers: list[CapacityAnswer] = Field(min_length=1, max_length=20)

class ReflectionItem(BaseModel):
    prompt_code: Literal["oportunidad", "motivacion"]
    text: str = Field(min_length=1, max_length=1000)

class ReflectionPayload(BaseModel):
    responses: list[ReflectionItem] = Field(min_length=1, max_length=2)

class CombPayload(BaseModel):
    phase: Literal["pre", "post", "reinforcement"] = "pre"
    # Cada diagnóstico tiene 3-4 afirmaciones; el tope evita inserciones masivas.
    responses: list[CombItem] = Field(min_length=1, max_length=20)
