from __future__ import annotations
import hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

_hasher = PasswordHasher()
EMAIL_CODE_LENGTH = 6

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False

def create_access_token(*, user_id: int, role: str, company_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "company_id": company_id, "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    # Solo se acepta el algoritmo configurado (nunca "none") y los claims básicos son obligatorios.
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "iat", "sub"]})

def new_email_code() -> str:
    """Código de 6 dígitos generado con un CSPRNG (secrets), no con random."""
    return f"{secrets.randbelow(10 ** EMAIL_CODE_LENGTH):0{EMAIL_CODE_LENGTH}d}"

def hash_email_code(challenge_id: str, code: str) -> str:
    """Solo se guarda el HMAC del código: si se filtra la base, no sirve para entrar.
    Va ligado al desafío, así un mismo código no vale en dos desafíos distintos."""
    key = settings.jwt_secret_key.encode()
    return hmac.new(key, f"{challenge_id}:{code}".encode(), hashlib.sha256).hexdigest()

def verify_email_code(challenge_id: str, code: str, expected_hash: str | None) -> bool:
    code = str(code)
    if not expected_hash or len(code) != EMAIL_CODE_LENGTH or not code.isdigit():
        return False
    return hmac.compare_digest(hash_email_code(challenge_id, code), expected_hash)
