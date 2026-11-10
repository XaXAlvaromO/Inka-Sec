from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_roles
from app.models.models import CombResponse
from app.repositories import module_repository
from app.services.dashboard_service import worker_dashboard
from app.schemas.content import CombPayload
from app.schemas.progress import ChallengeAnswer
from app.services import progress_service

router=APIRouter(prefix="/worker", tags=["worker"])

def _published_module(db: Session, module_id: int, user):
    # Un trabajador solo ve módulos publicados de su empresa (ni borradores ni de otras empresas).
    module = module_repository.get_for_company(db, module_id, user.company_id, published_only=True)
    if not module: raise HTTPException(404,"Módulo no encontrado")
    return module

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db), user=Depends(require_roles("worker"))): return worker_dashboard(db,user)
@router.get("/modules/{module_id}")
def module_detail(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    return _published_module(db,module_id,user).content_json
@router.post("/modules/{module_id}/comb")
def save_comb(module_id:int,payload:CombPayload,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    _published_module(db,module_id,user)
    for r in payload.responses:
        db.add(CombResponse(user_id=user.id,module_id=module_id,phase=payload.phase,dimension=r.dimension,prompt_code=r.code,value=r.value))
    db.commit(); return {"saved":len(payload.responses)}
@router.post("/modules/{module_id}/complete")
def complete(module_id:int,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: result=progress_service.mark_module_completed(db,user,module_id)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    return {"ok":True,"progress":100,**result}
@router.post("/challenges/{challenge_id}/answer")
def answer_challenge(challenge_id:int,payload:ChallengeAnswer,db:Session=Depends(get_db),user=Depends(require_roles("worker"))):
    try: return progress_service.submit_challenge_answer(db,user,challenge_id,payload.choice)
    except progress_service.NotFound as e: raise HTTPException(404,str(e))
    except progress_service.AlreadyAnswered as e: raise HTTPException(409,str(e))
    except progress_service.InvalidChoice as e: raise HTTPException(422,str(e))
