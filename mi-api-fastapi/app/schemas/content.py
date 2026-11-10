from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ContentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=180)
    topic: str = Field(default="General", max_length=100)
    description: str = Field(default="", max_length=2000)

class CombItem(BaseModel):
    dimension: Literal["capacidad", "oportunidad", "motivacion"]
    code: str = Field(min_length=1, max_length=30)
    value: int = Field(ge=1, le=5)

class CombPayload(BaseModel):
    phase: Literal["pre", "post", "reinforcement"] = "pre"
    # Cada diagnóstico tiene 3-4 afirmaciones; el tope evita inserciones masivas.
    responses: list[CombItem] = Field(min_length=1, max_length=20)
