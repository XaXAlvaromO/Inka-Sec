from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from reportlab.pdfgen import canvas
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.models.models import LearningModule, ModuleProgress, CombResponse, Certificate
from app.services.dashboard_service import worker_dashboard
from app.schemas.content import CombPayload, CompletePayload

router=APIRouter(prefix="/worker", tags=["worker"])
@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db), user=Depends(require_roles("worker"))): return worker_dashboard(db,user)
@router.get("/modules")
def modules(db:Session=Depends(get_db), user=Depends(require_roles("worker"))):
    rows=db.scalars(select(LearningModule).where(LearningModule.company_id==user.company_id,LearningModule.status=="published")).all()
    return [{"id":m.id,"slug":m.slug,"title":m.title,"topic":m.topic,"behavior_objective":m.behavior_objective} for m in rows]
@router.get("/modules/{module_id}")
def module_detail(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    m=db.get(LearningModule,module_id)
    if not m or m.company_id!=user.company_id: raise HTTPException(404,"Módulo no encontrado")
    return m.content_json
@router.post("/modules/{module_id}/comb")
def save_comb(module_id:int,payload:CombPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    for r in payload.responses:
        db.add(CombResponse(user_id=user.id,module_id=module_id,phase=payload.phase,dimension=r.dimension,prompt_code=r.code,value=r.value))
    db.commit(); return {"saved":len(payload.responses)}
@router.post("/modules/{module_id}/complete")
def complete(module_id:int,payload:CompletePayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    p=db.scalar(select(ModuleProgress).where(ModuleProgress.user_id==user.id,ModuleProgress.module_id==module_id))
    if not p: p=ModuleProgress(user_id=user.id,module_id=module_id); db.add(p)
    p.progress=100; p.score=float(payload.score); db.commit(); return {"ok":True,"progress":100,"score":p.score}
@router.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    cert=db.get(Certificate,certificate_id)
    if not cert or cert.user_id!=user.id: raise HTTPException(404,"Certificado no encontrado")
    bio=BytesIO(); c=canvas.Canvas(bio); c.setFont("Helvetica-Bold",22); c.drawString(80,760,"Certificado InkaSec"); c.setFont("Helvetica",13); c.drawString(80,720,f"Otorgado a: {user.name}"); c.drawString(80,695,f"Código: {cert.code}"); c.save()
    return Response(bio.getvalue(),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="certificado-{cert.code}.pdf"'})
