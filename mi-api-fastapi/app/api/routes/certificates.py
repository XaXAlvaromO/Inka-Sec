"""Verificación pública de certificados: cualquiera con el código puede comprobar si es válido."""
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from app.core.dependencies import client_ip
from app.core.middleware import RateLimiter
from app.db.session import get_db
from app.services import certificate_service

router = APIRouter(prefix="/certificates", tags=["certificates"])

# Sin sesión, así que se limita por IP para que nadie pruebe códigos al azar en masa.
verify_rate_limiter = RateLimiter(limit=30, window_seconds=60)


@router.get("/verify/{code}")
def verify(request: Request, code: str = Path(min_length=10, max_length=40, pattern=r"^[A-Za-z0-9-]+$"),
           db: Session = Depends(get_db)):
    if not verify_rate_limiter.allow(client_ip(request)):
        raise HTTPException(429, "Demasiadas consultas. Intenta en un minuto.")
    try:
        return certificate_service.verify(db, code)
    except certificate_service.NotFound as e:
        raise HTTPException(404, str(e))
