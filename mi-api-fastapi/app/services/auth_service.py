from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User, AuthChallenge
from app.core.security import verify_password, create_access_token, verify_totp
from app.services.audit_service import record_audit
from app.repositories.user_repository import get_by_email

LOCK_MINUTES = 15

def _normalize_dt(value):
    if value is None: return None
    if value.tzinfo is None: return value.replace(tzinfo=timezone.utc)
    return value

def login(db: Session, *, email: str, password: str, ip: str | None, user_agent: str | None):
    user = get_by_email(db, email)
    now = datetime.now(timezone.utc)
    if not user:
        record_audit(db, action="LOGIN_FAILED", result="denied", ip=ip, user_agent=user_agent, details={"email": email.lower().strip()})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    if not user.is_active:
        record_audit(db, action="LOGIN_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent, details={"reason":"inactive"})
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    locked_until = _normalize_dt(user.locked_until)
    if locked_until and locked_until > now:
        raise HTTPException(status_code=423, detail="Cuenta bloqueada temporalmente")
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 3:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        record_audit(db, action="LOGIN_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    if user.role in {"admin","manager"}:
        challenge = AuthChallenge(challenge_id=uuid4().hex, user_id=user.id, expires_at=now + timedelta(minutes=5))
        db.add(challenge); db.commit()
        return {"requires_2fa": True, "challenge_id": challenge.challenge_id, "email": user.email}, None, user
    token = create_access_token(user_id=user.id, role=user.role, company_id=user.company_id)
    record_audit(db, action="LOGIN_SUCCESS", result="success", user=user, ip=ip, user_agent=user_agent)
    return {"requires_2fa": False, "user": public_user(user)}, token, user

def verify_second_factor(db: Session, *, challenge_id: str, code: str, ip: str | None, user_agent: str | None):
    now = datetime.now(timezone.utc)
    challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.challenge_id == challenge_id))
    if not challenge or challenge.used_at is not None or _normalize_dt(challenge.expires_at) < now:
        raise HTTPException(status_code=401, detail="Desafío 2FA inválido o expirado")
    user = db.get(User, challenge.user_id)
    if not user or not user.totp_secret or not verify_totp(user.totp_secret, code):
        record_audit(db, action="MFA_FAILED", result="denied", user=user, ip=ip, user_agent=user_agent)
        raise HTTPException(status_code=401, detail="Código 2FA inválido")
    challenge.used_at = now; db.commit()
    token = create_access_token(user_id=user.id, role=user.role, company_id=user.company_id)
    record_audit(db, action="LOGIN_SUCCESS_MFA", result="success", user=user, ip=ip, user_agent=user_agent)
    return {"user": public_user(user)}, token, user

def public_user(user: User) -> dict:
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role,"area":user.area.name if user.area else None,"company_id":user.company_id}
