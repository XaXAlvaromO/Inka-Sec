from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.models.models import CombResponse
from app.services.dashboard_service import worker_dashboard
from app.schemas.content import CombPayload, CapacityPayload, ReflectionPayload
from fastapi.responses import Response
from app.models.models import Company
from app.schemas.progress import ChallengeAnswer, StepCheck, RenewalPayload
from app.services import progress_service, certificate_service
from app.services.certificate_pdf import render_certificate

router=APIRouter(prefix="/worker", tags=["worker"])

def _published_module(db: Session, module_id: int, user):
    # Solo módulos publicados de su empresa que le toquen (asignados a él, a su área o a toda la empresa).
    try: return progress_service.visible_module(db,user,module_id)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db), user=Depends(require_roles("worker"))): return worker_dashboard(db,user)
@router.get("/modules/{module_id}")
def module_detail(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    module=_published_module(db,module_id,user)
    return {**progress_service.worker_module_view(module.content_json),
            "saved_reflections":progress_service.saved_reflections(db,user,module_id),
            "saved_diagnostic":progress_service.saved_diagnostic(db,user,module_id),
            "resume_step":progress_service.resume_step(db,user,module_id)}
@router.post("/modules/{module_id}/capacity")
def grade_capacity(module_id:int,payload:CapacityPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: return progress_service.grade_capacity(db,user,module_id,[a.model_dump() for a in payload.answers])
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    except progress_service.InvalidChoice as e: raise HTTPException(422,str(e))
@router.post("/modules/{module_id}/reflections")
def save_reflections(module_id:int,payload:ReflectionPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: saved=progress_service.save_reflections(db,user,module_id,[r.model_dump() for r in payload.responses])
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    return {"saved":saved}
@router.post("/modules/{module_id}/comb")
def save_comb(module_id:int,payload:CombPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    _published_module(db,module_id,user)
    for r in payload.responses:
        row=db.scalar(select(CombResponse).where(CombResponse.user_id==user.id,CombResponse.module_id==module_id,
            CombResponse.phase==payload.phase,CombResponse.prompt_code==r.code))
        if row: row.value=r.value; row.dimension=r.dimension
        else: db.add(CombResponse(user_id=user.id,module_id=module_id,phase=payload.phase,dimension=r.dimension,prompt_code=r.code,value=r.value))
    db.commit(); return {"saved":len(payload.responses)}
@router.post("/modules/{module_id}/complete")
def complete(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: result=progress_service.mark_module_completed(db,user,module_id)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    return {"ok":True,"progress":100,**result}
@router.post("/challenges/{challenge_id}/answer")
def answer_challenge(challenge_id:int,payload:ChallengeAnswer,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    # Los retos se pueden repetir: cada envío es un intento más (entrenamiento, no sanción).
    try: return progress_service.submit_challenge_answer(db,user,challenge_id,choice=payload.choice,choices=payload.choices,marked=payload.marked)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    except progress_service.InvalidChoice as e: raise HTTPException(422,str(e))
@router.post("/challenges/{challenge_id}/check")
def check_step(challenge_id:int,payload:StepCheck,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: return progress_service.check_challenge_step(db,user,challenge_id,payload.step,payload.choice)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    except progress_service.InvalidChoice as e: raise HTTPException(422,str(e))

# ---------- Certificados (RF-07) ----------
@router.get("/certificates")
def certificates(db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    return certificate_service.worker_overview(db,user)
@router.get("/certificates/{cert_id}/renewal")
def renewal_quiz(cert_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: return certificate_service.renewal_quiz(db,user,cert_id)
    except certificate_service.NotFound as e: raise HTTPException(404,str(e))
    except certificate_service.NotRenewable as e: raise HTTPException(409,str(e))
@router.post("/certificates/{cert_id}/renewal")
def renew(cert_id:int,payload:RenewalPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: return certificate_service.renew(db,user,cert_id,[a.model_dump() for a in payload.answers])
    except certificate_service.NotFound as e: raise HTTPException(404,str(e))
    except certificate_service.NotRenewable as e: raise HTTPException(409,str(e))
    except certificate_service.InvalidAnswers as e: raise HTTPException(422,str(e))
@router.get("/certificates/{cert_id}/pdf")
def certificate_pdf(cert_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    cert=db.get(certificate_service.Certificate,cert_id)
    if not cert or cert.user_id!=user.id: raise HTTPException(404,"Certificado no encontrado")
    company=db.get(Company,cert.company_id)
    pdf=render_certificate(cert,holder=user.name,company=company.name if company else "",status=certificate_service.status_of(cert))
    return Response(pdf,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="certificado-{cert.code}.pdf"',"Cache-Control":"no-store"})
