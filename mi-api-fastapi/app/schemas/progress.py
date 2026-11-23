from pydantic import BaseModel, Field


class ChallengeAnswer(BaseModel):
    """Una sola de las tres llaves, según el formato del reto."""
    choice: int | None = Field(default=None, ge=0, le=20, description="Reto rápido: índice de la opción elegida")
    choices: list[int] | None = Field(default=None, max_length=5, description="Escenario por pasos: una opción por paso")
    marked: list[int] | None = Field(default=None, max_length=12, description="Encuentra las señales: fragmentos marcados")


class StepCheck(BaseModel):
    step: int = Field(ge=0, le=4)
    choice: int = Field(ge=0, le=3)


class RenewalAnswer(BaseModel):
    key: str = Field(min_length=3, max_length=20, pattern=r"^\d+:\d+$")
    choice: int = Field(ge=0, le=3)


class RenewalPayload(BaseModel):
    answers: list[RenewalAnswer] = Field(min_length=1, max_length=60)
