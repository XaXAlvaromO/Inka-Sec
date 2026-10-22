from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.models.models import LearningModule
from app.services.dashboard_service import manager_dashboard
from app.services.audit_service import record_audit
from app.schemas.content import ContentCreate
router=APIRouter(prefix="/manager",tags=["manager"])
@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),user=Depends(require_roles("manager"))): return manager_dashboard(db,user)
@router.post("/content")
def create_content(payload:ContentCreate,db:Session=Depends(get_db),user=Depends(require_roles("manager"))):
    title=payload.title.strip(); topic=payload.topic.strip()
    slug=title.lower().replace(" ","-")[:100] or "nuevo-modulo"
    m=LearningModule(company_id=user.company_id,slug=slug,title=title or "Nuevo módulo",topic=topic,behavior_objective=payload.description or "Conducta por definir",status="draft",content_json={"title":title,"topic":topic,"description":payload.description},created_by=user.id)
    db.add(m); db.commit(); db.refresh(m); record_audit(db,action="MODULE_CREATED",result="success",user=user,details={"module_id":m.id})
    return {"id":m.id,"title":m.title,"type":"Módulo","status":"Borrador","users":0,"success":None,"updated":m.updated_at.isoformat()}
@router.get("/content/{module_id}")
def get_content(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("manager"))):
    m=db.get(LearningModule,module_id); return m.content_json if m and m.company_id==user.company_id else {}
