from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User
from app.core.security import decode_access_token

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("inka_access")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    # Complete mediation: role is checked on each request by dependencies below.
    return user

def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="No autorizado para este recurso")
        return user
    return dependency
