from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["worker", "manager", "admin"]
ROLE_LABELS = {"worker": "Trabajador", "manager": "Gestor", "admin": "Administrador"}
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180, pattern=EMAIL_PATTERN)
    area: str = Field(min_length=2, max_length=100)
    role: Role = "worker"

class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None

def user_row(u) -> dict:
    """Representación de un usuario en las tablas del panel de administración."""
    return {"id":u.id,"name":u.name,"email":u.email,"area":u.area.name if u.area else "Sin área","role":ROLE_LABELS.get(u.role,u.role),"status":"Activo" if u.is_active else "Inactivo","twoFactor":bool(u.totp_secret)}
