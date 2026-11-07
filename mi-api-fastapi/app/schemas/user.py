from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["worker", "manager", "admin"]

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    area: str = Field(min_length=2, max_length=100)
    role: Role = "worker"

class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
