from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import client_ip, require_roles
from app.schemas.superadmin import CompanyCreate
from app.schemas.user import UserUpdate
from app.services import superadmin_service as svc

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


@router.get("/companies")
def companies(db: Session = Depends(get_db), user=Depends(require_roles("superadmin"))):
    return svc.list_companies(db)


@router.post("/companies", status_code=201)
def create_company(payload: CompanyCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("superadmin"))):
    return svc.create_company(db, actor=user, company_name=payload.company_name, admin_name=payload.admin_name, admin_email=payload.admin_email, ip=client_ip(request))


@router.get("/companies/{company_id}/users")
def company_users(company_id: int, db: Session = Depends(get_db), user=Depends(require_roles("superadmin"))):
    return svc.list_company_users(db, company_id)


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("superadmin"))):
    return svc.update_any_user(db, actor=user, user_id=user_id, payload=payload, ip=client_ip(request))


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("superadmin"))):
    return svc.delete_any_user(db, actor=user, user_id=user_id, ip=client_ip(request))
