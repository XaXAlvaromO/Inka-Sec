from __future__ import annotations
import base64, hashlib, hmac, os, struct, time
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

_hasher = PasswordHasher()

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
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

def new_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode().rstrip("=")

def _b32decode(secret: str) -> bytes:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded, casefold=True)

def totp_code(secret: str, at_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    counter = int((at_time or time.time()) // step)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(_b32decode(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7fffffff) % (10 ** digits)
    return str(value).zfill(digits)

def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + i*30), str(code).zfill(6)) for i in range(-window, window+1))
