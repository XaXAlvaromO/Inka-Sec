from typing import Literal
from pydantic import BaseModel, Field

class ContentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    topic: str = Field(default="General", max_length=100)
    description: str = Field(default="", max_length=2000)

class CombItem(BaseModel):
    dimension: Literal["capacidad", "oportunidad", "motivacion"]
    code: str = Field(min_length=1, max_length=30)
    value: int = Field(ge=1, le=5)

class CombPayload(BaseModel):
    phase: Literal["pre", "post", "reinforcement"] = "pre"
    responses: list[CombItem]

class CompletePayload(BaseModel):
    score: float = Field(default=100, ge=0, le=100)
