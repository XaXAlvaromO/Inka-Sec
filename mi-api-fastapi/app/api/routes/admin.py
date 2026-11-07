from io import StringIO
import csv
import secrets
from fastapi import APIRouter, Depends, Request, Response, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.core.security import hash_password, new_totp_secret
from app.models.models import User, Area, AuditLog
from app.services.admin_report_service import admin_report_summary
from app.services.dashboard_service import admin_dashboard
from app.services.audit_service import record_audit
from app.schemas.user import UserCreate, UserUpdate
router=APIRouter(prefix="/admin",tags=["admin"])
AUDIT_ACTION_LABELS={"LOGIN_SUCCESS":"Inicio de sesión","LOGIN_SUCCESS_MFA":"Inicio de sesión con 2FA","LOGIN_FAILED":"Inicio de sesión fallido","MFA_FAILED":"Verificación 2FA fallida","USER_CREATED":"Usuario creado","USER_UPDATED":"Usuario actualizado","USER_DELETED":"Usuario eliminado","ROLE_CHANGED":"Rol actualizado","AREA_CREATED":"Área creada"}

class AreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)

def user_row(u: User):
    return {"id":u.id,"name":u.name,"email":u.email,"area":u.area.name if u.area else "Sin área","role":{"worker":"Trabajador","manager":"Gestor","admin":"Administrador"}.get(u.role,u.role),"status":"Activo" if u.is_active else "Inactivo","twoFactor":bool(u.totp_secret)}

def csv_text(value: str) -> str:
    return "'"+value if value.startswith(("=","+","-","@","\t","\r","\n")) else value

def area_rows(db: Session, company_id: int):
    rows=db.execute(select(Area.id,Area.name,func.count(User.id),func.sum(case((User.role=="manager",1),else_=0))).outerjoin(User,and_(User.area_id==Area.id,User.company_id==company_id)).where(Area.company_id==company_id).group_by(Area.id,Area.name).order_by(Area.name)).all()
    return [{"id":area_id,"name":name,"users":users,"managers":managers or 0} for area_id,name,users,managers in rows]

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user=Depends(require_roles("admin"))): return admin_dashboard(db,user)
@router.get("/users")
def users(db:Session=Depends(get_db),user=Depends(require_roles("admin"))):
    rows=db.scalars(select(User).where(User.company_id==user.company_id).order_by(User.id)).all(); return [user_row(u) for u in rows]
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
    return {**user_row(u),"temporary_password":temporary_password,"totp_setup_secret":secret}
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

@router.get("/areas")
def areas(db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    return area_rows(db,admin.company_id)

@router.post("/areas",status_code=201)
def create_area(payload:AreaCreate,request:Request,db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    name=payload.name.strip()
    if len(name)<2: raise HTTPException(422,"El nombre del área debe tener al menos 2 caracteres")
    existing=db.scalar(select(Area).where(Area.company_id==admin.company_id,func.lower(Area.name)==name.lower()))
    if existing: raise HTTPException(409,"El área ya existe")
    area=Area(company_id=admin.company_id,name=name)
    db.add(area); db.commit(); db.refresh(area)
    record_audit(db,action="AREA_CREATED",result="success",user=admin,ip=request.client.host if request.client else None,details={"area_id":area.id,"name":name})
    return {"id":area.id,"name":area.name,"users":0,"managers":0}

@router.get("/audit")
def audit(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),q:str=Query("",max_length=100),db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    rows=select(AuditLog,User.name).outerjoin(User,User.id==AuditLog.user_id).where(AuditLog.company_id==admin.company_id)
    count=select(func.count(AuditLog.id)).outerjoin(User,User.id==AuditLog.user_id).where(AuditLog.company_id==admin.company_id)
    if q.strip():
        pattern=f"%{q.strip()}%"
        matching_actions=[action for action,label in AUDIT_ACTION_LABELS.items() if q.strip().lower() in label.lower()]
        predicate=or_(AuditLog.action.ilike(pattern),AuditLog.action.in_(matching_actions),AuditLog.ip_address.ilike(pattern),User.name.ilike(pattern))
        rows=rows.where(predicate); count=count.where(predicate)
    total=db.scalar(count) or 0
    page=db.execute(rows.order_by(AuditLog.created_at.desc(),AuditLog.id.desc()).offset(offset).limit(limit)).all()
    return {"items":[{"id":a.id,"type":"danger" if a.result!="success" else "success","action":a.action,"actor":actor or "Usuario eliminado o desconocido","ip":a.ip_address,"time":a.created_at.isoformat()} for a,actor in page],"total":total,"limit":limit,"offset":offset}

@router.get("/reports/summary")
def report_summary(db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    return admin_report_summary(db,admin.company_id)

@router.get("/reports/export")
def export_report(db:Session=Depends(get_db),admin=Depends(require_roles("admin"))):
    report=admin_report_summary(db,admin.company_id); sio=StringIO(); w=csv.writer(sio); w.writerow(["area","usuarios","usuarios_activos","avance_promedio_registrado","modulos_completados"])
    for area in report["areas"]: w.writerow([csv_text(area["name"]),area["users"],area["active_users"],area["average_progress"] if area["average_progress"] is not None else "",area["completed_modules"]])
    return Response(sio.getvalue(),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=inkasec-reporte.csv"})
