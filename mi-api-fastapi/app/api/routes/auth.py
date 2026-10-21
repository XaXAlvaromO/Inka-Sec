from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
import secrets
from app.db.session import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.services.auth_service import login, verify_second_factor, public_user
from app.schemas.auth import LoginIn, Verify2FAIn

router=APIRouter(prefix="/auth", tags=["auth"])

def client_ip(request: Request):
    forwarded=request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)

def set_access_cookie(response: Response, token: str):
    response.set_cookie("inka_access",token,httponly=True,secure=settings.cookie_secure,samesite=settings.cookie_samesite,max_age=settings.access_token_minutes*60,path="/")
    csrf=secrets.token_urlsafe(32)
    response.set_cookie("inka_csrf",csrf,httponly=False,secure=settings.cookie_secure,samesite=settings.cookie_samesite,max_age=settings.access_token_minutes*60,path="/")

@router.post("/login")
def login_route(payload:LoginIn, request:Request, response:Response, db:Session=Depends(get_db)):
    result,token,_=login(db,email=payload.email,password=payload.password,ip=client_ip(request),user_agent=request.headers.get("user-agent"))
    if token: set_access_cookie(response,token)
    return result

@router.post("/2fa/verify")
def verify_2fa_route(payload:Verify2FAIn, request:Request, response:Response, db:Session=Depends(get_db)):
    result,token,_=verify_second_factor(db,challenge_id=payload.challenge_id,code=payload.code,ip=client_ip(request),user_agent=request.headers.get("user-agent"))
    set_access_cookie(response,token); return result

@router.get("/me")
def me(user=Depends(get_current_user)): return {"user":public_user(user)}

@router.post("/logout")
def logout(response:Response):
    response.delete_cookie("inka_access",path="/"); response.delete_cookie("inka_csrf",path="/"); return {"ok":True}
