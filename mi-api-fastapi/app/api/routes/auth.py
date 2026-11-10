from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
import secrets
from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import client_ip, get_current_user
from app.services.auth_service import login, verify_second_factor, public_user
from app.schemas.auth import LoginIn, Verify2FAIn

router=APIRouter(prefix="/auth", tags=["auth"])

def _cookie_options(httponly: bool) -> dict:
    return {"httponly": httponly, "secure": settings.cookie_secure, "samesite": settings.cookie_samesite, "path": "/"}

def set_access_cookie(response: Response, token: str):
    max_age = settings.access_token_minutes*60
    response.set_cookie("inka_access",token,max_age=max_age,**_cookie_options(httponly=True))
    response.set_cookie("inka_csrf",secrets.token_urlsafe(32),max_age=max_age,**_cookie_options(httponly=False))

@router.post("/login")
def login_route(payload:LoginIn, request:Request, response:Response, db:Session=Depends(get_db)):
    result,token=login(db,email=payload.email,password=payload.password,ip=client_ip(request),user_agent=request.headers.get("user-agent"))
    if token: set_access_cookie(response,token)
    return result

@router.post("/2fa/verify")
def verify_2fa_route(payload:Verify2FAIn, request:Request, response:Response, db:Session=Depends(get_db)):
    result,token=verify_second_factor(db,challenge_id=payload.challenge_id,code=payload.code,ip=client_ip(request),user_agent=request.headers.get("user-agent"))
    set_access_cookie(response,token); return result

@router.get("/me")
def me(user=Depends(get_current_user)): return {"user":public_user(user)}

@router.post("/logout")
def logout(response:Response):
    # Mismos atributos que al crearlas: si no coinciden, el navegador puede ignorar el borrado.
    response.delete_cookie("inka_access",**_cookie_options(httponly=True))
    response.delete_cookie("inka_csrf",**_cookie_options(httponly=False))
    return {"ok":True}
