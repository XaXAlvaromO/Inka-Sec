"""Entradas del Panel de Contenido (gestor). Las reglas de negocio viven en content_service."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _check_options(options: list[str], correct: int) -> None:
    if any(not option.strip() or len(option) > 200 for option in options):
        raise ValueError("Cada opción debe tener entre 1 y 200 caracteres")
    if correct >= len(options):
        raise ValueError("La respuesta correcta debe ser una de las opciones")


class QuestionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    prompt: str = Field(min_length=5, max_length=300)
    options: list[str] = Field(min_length=2, max_length=4)
    correct: int = Field(ge=0, le=3)
    feedback: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def _valid(self):
        _check_options(self.options, self.correct)
        return self


class ModuleIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=180)
    topic: str = Field(min_length=1, max_length=100)
    objective: str = Field(min_length=10, max_length=400)
    micro_lesson: str = Field(min_length=20, max_length=1200)
    capacity_questions: list[QuestionIn] = Field(min_length=1, max_length=5)
    opportunity_question: str = Field(default="¿Qué te dificulta aplicar esto en tu trabajo?", min_length=5, max_length=300)
    motivation_question: str = Field(default="¿Por qué te importa este tema para tu trabajo?", min_length=5, max_length=300)
    real_action: str = Field(min_length=5, max_length=500)
    status: Literal["draft", "published", "archived"] = "draft"


class ChallengeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=180)
    topic: str = Field(min_length=1, max_length=100)
    scenario: str = Field(min_length=20, max_length=1000)
    options: list[str] = Field(min_length=2, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    feedback: str = Field(default="", max_length=300)
    status: Literal["draft", "published", "archived"] = "draft"

    @model_validator(mode="after")
    def _valid(self):
        _check_options(self.options, self.correct_index)
        return self


class AssignmentIn(BaseModel):
    item_type: Literal["module", "challenge"]
    item_id: int = Field(ge=1)
    target: Literal["company", "area", "user"]
    area_id: int | None = Field(default=None, ge=1)
    user_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None

    @model_validator(mode="after")
    def _target(self):
        if self.target == "area" and (self.area_id is None or self.user_id is not None):
            raise ValueError("Elige un área")
        if self.target == "user" and (self.user_id is None or self.area_id is not None):
            raise ValueError("Elige un trabajador")
        if self.target == "company" and (self.area_id is not None or self.user_id is not None):
            raise ValueError("La asignación a toda la empresa no lleva área ni persona")
        return self
