from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    # Tope de longitud: Argon2 sobre contraseñas gigantes sería un vector de DoS.
    password: str = Field(min_length=1, max_length=256)

class Verify2FAIn(BaseModel):
    challenge_id: str = Field(min_length=32, max_length=64, pattern=r"^[0-9a-f]+$")
    code: str = Field(pattern=r"^\d{6}$")
