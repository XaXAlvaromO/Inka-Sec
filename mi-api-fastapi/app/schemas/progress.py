from pydantic import BaseModel, Field


class ChallengeAnswer(BaseModel):
    choice: int = Field(ge=0, le=20, description="Índice de la opción elegida")
