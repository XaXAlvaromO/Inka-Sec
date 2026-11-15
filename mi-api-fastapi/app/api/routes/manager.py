from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import client_ip, require_roles
from app.core.topics import TOPICS
from app.services import content_service
from app.services.dashboard_service import manager_dashboard
from app.services.audit_service import record_audit
from app.schemas.manager import AssignmentIn, ChallengeIn, ModuleIn

router = APIRouter(prefix="/manager", tags=["manager"])


def _http(error: content_service.ContentError) -> HTTPException:
    return HTTPException(error.status, str(error))


@router.get("/topics")
def topics(user=Depends(require_roles("manager"))):
    return {"topics": list(TOPICS)}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    return manager_dashboard(db, user)


# ---------- Módulos (HU-07) ----------

@router.get("/modules/{module_id}")
def get_module(module_id: int, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        return content_service.module_form(db, user, module_id)
    except content_service.ContentError as e:
        raise _http(e)


@router.post("/modules")
def create_module(payload: ModuleIn, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        module = content_service.create_module(db, user, payload)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="MODULE_CREATED", result="success", user=user, ip=client_ip(request), details={"module_id": module.id})
    return {"id": module.id, "title": module.title, "status": module.status}


@router.put("/modules/{module_id}")
def update_module(module_id: int, payload: ModuleIn, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        module = content_service.update_module(db, user, module_id, payload)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="MODULE_UPDATED", result="success", user=user, ip=client_ip(request), details={"module_id": module.id})
    return {"id": module.id, "title": module.title, "status": module.status}


# ---------- Retos (HU-07) ----------

@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        return content_service.challenge_form(db, user, challenge_id)
    except content_service.ContentError as e:
        raise _http(e)


@router.post("/challenges")
def create_challenge(payload: ChallengeIn, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        challenge = content_service.create_challenge(db, user, payload)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="CHALLENGE_CREATED", result="success", user=user, ip=client_ip(request), details={"challenge_id": challenge.id})
    return {"id": challenge.id, "title": challenge.title, "status": challenge.status}


@router.put("/challenges/{challenge_id}")
def update_challenge(challenge_id: int, payload: ChallengeIn, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        challenge = content_service.update_challenge(db, user, challenge_id, payload)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="CHALLENGE_UPDATED", result="success", user=user, ip=client_ip(request), details={"challenge_id": challenge.id})
    return {"id": challenge.id, "title": challenge.title, "status": challenge.status}


# ---------- Asignaciones y fechas límite (HU-09) ----------

@router.get("/assignable")
def assignable(db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    return content_service.assignable_items(db, user)


@router.get("/assignments")
def list_assignments(db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    return content_service.assignments_view(db, user)


@router.post("/assignments")
def create_assignment(payload: AssignmentIn, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        assignment = content_service.create_assignment(db, user, payload)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="ASSIGNMENT_CREATED", result="success", user=user, ip=client_ip(request), details={"assignment_id": assignment.id})
    return {"id": assignment.id}


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    try:
        content_service.delete_assignment(db, user, assignment_id)
    except content_service.ContentError as e:
        raise _http(e)
    record_audit(db, action="ASSIGNMENT_DELETED", result="success", user=user, ip=client_ip(request), details={"assignment_id": assignment_id})
    return {"ok": True}


# ---------- Estadísticas (HU-10) ----------

@router.get("/stats")
def stats(db: Session = Depends(get_db), user=Depends(require_roles("manager"))):
    return content_service.stats(db, user)
