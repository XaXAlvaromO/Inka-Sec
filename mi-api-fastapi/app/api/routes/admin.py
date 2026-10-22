from io import StringIO
import csv
import secrets
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.core.security import hash_password, new_totp_secret
from app.models.models import User, Area
from app.services.dashboard_service import admin_dashboard
from app.services.audit_service import record_audit
from app.schemas.user import UserCreate, UserUpdate
router=APIRouter(prefix="/admin",tags=["admin"])
@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user=Depends(require_roles("admin"))): return admin_dashboard(db,user)
@router.get("/users")
def users(db:Session=Depends(get_db),user=Depends(require_roles("admin"))):
    rows=db.scalars(select(User).where(User.company_id==user.company_id)).all(); return [{"id":u.id,"name":u.name,"email":u.email,"role":u.role,"active":u.is_active} for u in rows]
@router.post("/users")
def create_user(payload:UserCreate,request:Request,db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    email=payload.email.lower().strip()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"El correo ya existe")
    area_name=payload.area; area=db.scalar(select(Area).where(Area.company_id==admin.company_id,Area.name==area_name))
    if not area: area=Area(company_id=admin.company_id,name=area_name); db.add(area); db.commit(); db.refresh(area)
    role=payload.role
    secret=new_totp_secret() if role in {"manager","admin"} else None
    temporary_password=secrets.token_urlsafe(15)
    u=User(company_id=admin.company_id,area_id=area.id,name=payload.name,email=email,password_hash=hash_password(temporary_password),role=role,totp_secret=secret,is_active=True)
    db.add(u); db.commit(); db.refresh(u); record_audit(db,action="USER_CREATED",result="success",user=admin,ip=request.client.host if request.client else None,details={"target_user_id":u.id,"role":role})
    return {"id":u.id,"name":u.name,"email":u.email,"area":area.name,"role":role,"status":"Activo","progress":0,"twoFactor":bool(secret),"temporary_password":temporary_password,"totp_setup_secret":secret}
@router.patch("/users/{user_id}")
def update_user(user_id:int,payload:UserUpdate,request:Request,db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    u=db.get(User,user_id)
    if not u or u.company_id!=admin.company_id: raise HTTPException(404,"Usuario no encontrado")
    old_role=u.role
    if payload.role is not None:
        u.role=payload.role
        if u.role in {"manager","admin"} and not u.totp_secret: u.totp_secret=new_totp_secret()
    if payload.is_active is not None: u.is_active=payload.is_active
    db.commit(); record_audit(db,action="ROLE_CHANGED" if old_role!=u.role else "USER_UPDATED",result="success",user=admin,ip=request.client.host if request.client else None,details={"target_user_id":u.id,"old_role":old_role,"new_role":u.role})
    return {"ok":True}
@router.delete("/users/{user_id}")
def delete_user(user_id:int,request:Request,db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    u=db.get(User,user_id)
    if not u or u.company_id!=admin.company_id: raise HTTPException(404,"Usuario no encontrado")
    target=u.id; db.delete(u); db.commit(); record_audit(db,action="USER_DELETED",result="success",user=admin,ip=request.client.host if request.client else None,details={"target_user_id":target}); return {"ok":True}
@router.get("/reports/export")
def export_report(db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    areas=db.scalars(select(Area).where(Area.company_id==admin.company_id)).all(); sio=StringIO(); w=csv.writer(sio); w.writerow(["area","usuarios"])
    for a in areas: w.writerow([a.name, len(db.scalars(select(User).where(User.company_id==admin.company_id,User.area_id==a.id)).all())])
    return Response(sio.getvalue(),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=inkasec-reporte.csv"})
