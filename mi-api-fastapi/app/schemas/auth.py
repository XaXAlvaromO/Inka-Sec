from pydantic import BaseModel

class LoginIn(BaseModel):
    email: str
    password: str

class Verify2FAIn(BaseModel):
    challenge_id: str
    code: str
