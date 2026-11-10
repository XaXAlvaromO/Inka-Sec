import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User, AuthChallenge
from app.core.security import hash_password, verify_password, create_access_token, verify_totp
from app.services.audit_service import record_audit
from app.repositories.user_repository import get_by_email, normalize_email

LOCK_MINUTES = 15
MAX_FAILED_ATTEMPTS = 3
CHALLENGE_MINUTES = 5
ROLES_WITH_2FA = {"admin", "manager"}

def _normalize_dt(value):
    if value is None: return None
    if value.tzinfo is None: return value.replace(tzinfo=timezone.utc)
    return value

@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))

def _is_locked(user: User, now: datetime) -> bool:
    locked_until = _normalize_dt(user.locked_until)
    return bool(locked_until and locked_until > now)

def _register_failure(db: Session, user: User, now: datetime):
    """Contraseña o código 2FA incorrecto: suma al mismo contador y bloquea al llegar al límite."""
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        user.failed_login_attempts = 0
    db.commit()

def _clear_failures(user: User):
    user.failed_login_attempts = 0
    user.locked_until = None

def login(db: Session, *, email: str, password: str, ip: str | None, user_agent: str | None):
    user = get_by_email(db, email)
    now = datetime.now(timezone.utc)
    if not user:
        # Se calcula un hash igual: sin esto, la respuesta rápida revela qué correos existen.
        verify_password(password, _dummy_hash())
        record_audit(db, action="LOGIN_FAILED", result="denied", ip=ip, user_agent=user_agent, details={"email": normalize_email(email)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if _is_locked(user, now):
        raise HTTPException(status_code=423, detail="Cuenta bloqueada temporalmente")
    if not verify_password(password, user.password_hash):
        _register_failure(db, user, now)
        record_audit(db, action="LOGIN_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not user.is_active:
        # Solo se informa a quien ya conoce la contraseña.
        record_audit(db, action="LOGIN_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent, details={"reason":"inactive"})
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    if user.role in ROLES_WITH_2FA:
        # El contador de fallos no se limpia aquí, sino al superar el 2FA. Si no, volver
        # a iniciar sesión daría intentos ilimitados para adivinar el código.
        challenge = AuthChallenge(challenge_id=uuid4().hex, user_id=user.id, expires_at=now + timedelta(minutes=CHALLENGE_MINUTES))
        db.add(challenge); db.commit()
        return {"requires_2fa": True, "challenge_id": challenge.challenge_id, "email": user.email}, None
    _clear_failures(user)
    db.commit()
    token = create_access_token(user_id=user.id, role=user.role, company_id=user.company_id)
    record_audit(db, action="LOGIN_SUCCESS", result="success", user=user, ip=ip, user_agent=user_agent)
    return {"requires_2fa": False, "user": public_user(user)}, token

def _burn(db: Session, challenge: AuthChallenge, now: datetime) -> bool:
    """Marca el desafío como usado de forma atómica. False si otra petición ya lo usó."""
    result = db.execute(update(AuthChallenge).where(AuthChallenge.id == challenge.id, AuthChallenge.used_at.is_(None)).values(used_at=now))
    db.commit()
    return result.rowcount == 1

def verify_second_factor(db: Session, *, challenge_id: str, code: str, ip: str | None, user_agent: str | None):
    now = datetime.now(timezone.utc)
    invalid = HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")
    challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.challenge_id == challenge_id))
    if not challenge or challenge.used_at is not None or _normalize_dt(challenge.expires_at) < now:
        raise invalid
    user = db.get(User, challenge.user_id)
    if not user or not user.is_active:
        _burn(db, challenge, now)
        raise invalid
    if _is_locked(user, now):
        _burn(db, challenge, now)
        raise HTTPException(status_code=423, detail="Cuenta bloqueada temporalmente")
    if not user.totp_secret or not verify_totp(user.totp_secret, code):
        _register_failure(db, user, now)
        if _is_locked(user, now):
            _burn(db, challenge, now)
        record_audit(db, action="MFA_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent)
        raise HTTPException(status_code=401, detail="Código 2FA inválido")
    if not _burn(db, challenge, now):
        raise invalid
    _clear_failures(user)
    db.commit()
    token = create_access_token(user_id=user.id, role=user.role, company_id=user.company_id)
    record_audit(db, action="LOGIN_SUCCESS_MFA", result="success", user=user, ip=ip, user_agent=user_agent)
    return {"user": public_user(user)}, token

def public_user(user: User) -> dict:
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role,"area":user.area.name if user.area else None,"company_id":user.company_id}
