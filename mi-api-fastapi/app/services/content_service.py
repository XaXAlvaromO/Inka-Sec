"""Panel de Contenido del gestor (HU-07 a HU-10).

- Crear y editar: solo el contenido que el gestor creó (los módulos base de la empresa son de lectura).
- Asignar: cualquier contenido publicado de la empresa, con fecha límite opcional.
- Estadísticas: solo del contenido que el gestor creó. Módulos: quién terminó. Retos: solo quién
  practicó; los aciertos se muestran agregados y únicamente con 3 o más personas (el reto entrena,
  no sanciona).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.topics import TOPICS
from app.models.challenge import Challenge, ChallengeAttempt
from app.models.models import Area, Assignment, LearningModule, ModuleProgress, User, utcnow
from app.repositories import progress_repository
from app.services import visibility
from app.services import certificate_service
from app.services.progress_service import MIN_GROUP, rate, topic_errors_for

STATUS_LABEL = {"published": "Publicado", "draft": "Borrador", "archived": "Archivado"}

DEFAULT_DIAGNOSTIC_OPPORTUNITY = "Tengo las herramientas o el apoyo necesario para ponerlo en práctica."
DEFAULT_DIAGNOSTIC_MOTIVATION = "Creo que este tema reduce un riesgo real para mi trabajo."


class ContentError(Exception):
    status = 422


class NotFound(ContentError):
    status = 404


class Forbidden(ContentError):
    status = 403


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:90] or "contenido"


def _unique_slug(db: Session, company_id: int, title: str) -> str:
    base = slugify(title)
    slug, n = base, 2
    while db.scalar(select(LearningModule.id).where(LearningModule.company_id == company_id, LearningModule.slug == slug)):
        slug = f"{base}-{n}"
        n += 1
    return slug


def _check_topic(topic: str, current: str | None = None) -> None:
    # El tema actual de un contenido heredado se conserva al editarlo aunque no esté en el catálogo.
    if topic not in TOPICS and topic != current:
        raise ContentError("Elige un tema de la lista")


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ---------- Módulos ----------

def _module_content(payload, slug: str) -> dict:
    return {
        "slug": slug,
        "title": payload.title,
        "topic": payload.topic,
        "behavior_objective": payload.objective,
        "source": "Creado por el gestor de contenido",
        "diagnostic": [
            {"code": "C1", "dimension": "capacidad", "statement": f"Sé aplicar lo que enseña este módulo sobre {payload.topic.lower()}."},
            {"code": "O1", "dimension": "oportunidad", "statement": DEFAULT_DIAGNOSTIC_OPPORTUNITY},
            {"code": "M1", "dimension": "motivacion", "statement": DEFAULT_DIAGNOSTIC_MOTIVATION},
        ],
        "micro_lesson": payload.micro_lesson,
        "capacity_questions": [q.model_dump() for q in payload.capacity_questions],
        "opportunity_question": payload.opportunity_question,
        "motivation_question": payload.motivation_question,
        "real_action": payload.real_action,
    }


def _owned_module(db: Session, manager: User, module_id: int) -> LearningModule:
    module = db.get(LearningModule, module_id)
    if not module or module.company_id != manager.company_id:
        raise NotFound("Contenido no encontrado")
    if module.created_by != manager.id:
        raise Forbidden("Solo puedes editar el contenido que creaste")
    return module


def create_module(db: Session, manager: User, payload) -> LearningModule:
    _check_topic(payload.topic)
    slug = _unique_slug(db, manager.company_id, payload.title)
    module = LearningModule(
        company_id=manager.company_id, slug=slug, title=payload.title, topic=payload.topic,
        behavior_objective=payload.objective, status=payload.status,
        content_json=_module_content(payload, slug), created_by=manager.id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def update_module(db: Session, manager: User, module_id: int, payload) -> LearningModule:
    module = _owned_module(db, manager, module_id)
    _check_topic(payload.topic, current=module.topic)
    module.title = payload.title
    module.topic = payload.topic
    module.behavior_objective = payload.objective
    module.status = payload.status
    module.content_json = _module_content(payload, module.slug)
    db.commit()
    db.refresh(module)
    return module


def module_form(db: Session, manager: User, module_id: int) -> dict:
    module = _owned_module(db, manager, module_id)
    content = module.content_json or {}
    return {
        "id": module.id, "title": module.title, "topic": module.topic, "objective": module.behavior_objective,
        "micro_lesson": content.get("micro_lesson", ""),
        "capacity_questions": [
            {"prompt": q.get("prompt", ""), "options": list(q.get("options", [])),
             "correct": q.get("correct", 0), "feedback": q.get("feedback", "")}
            for q in content.get("capacity_questions", [])
        ],
        "opportunity_question": content.get("opportunity_question", ""),
        "motivation_question": content.get("motivation_question", ""),
        "real_action": content.get("real_action", ""),
        "status": module.status,
    }


# ---------- Retos ----------

def _owned_challenge(db: Session, manager: User, challenge_id: int) -> Challenge:
    challenge = db.get(Challenge, challenge_id)
    if not challenge or challenge.company_id != manager.company_id:
        raise NotFound("Reto no encontrado")
    if challenge.created_by != manager.id:
        raise Forbidden("Solo puedes editar el reto que creaste")
    return challenge


def create_challenge(db: Session, manager: User, payload) -> Challenge:
    _check_topic(payload.topic)
    challenge = Challenge(
        company_id=manager.company_id, title=payload.title, topic=payload.topic, scenario=payload.scenario,
        kind=payload.kind, content=payload.content(),
        options=list(payload.options) if payload.kind == "quick" else [],
        correct_index=payload.correct_index if payload.kind == "quick" else 0, feedback=payload.feedback,
        status=payload.status, created_by=manager.id,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def update_challenge(db: Session, manager: User, challenge_id: int, payload) -> Challenge:
    challenge = _owned_challenge(db, manager, challenge_id)
    _check_topic(payload.topic, current=challenge.topic)
    current_kind = challenge.kind or "quick"
    if payload.kind != current_kind and db.scalar(select(ChallengeAttempt.id).where(ChallengeAttempt.challenge_id == challenge.id).limit(1)):
        raise ContentError("Este reto ya tiene intentos: no puedes cambiar su formato. Crea un reto nuevo.")
    challenge.title = payload.title
    challenge.topic = payload.topic
    challenge.scenario = payload.scenario
    challenge.kind = payload.kind
    challenge.content = payload.content()
    challenge.options = list(payload.options) if payload.kind == "quick" else []
    challenge.correct_index = payload.correct_index if payload.kind == "quick" else 0
    challenge.feedback = payload.feedback
    challenge.status = payload.status
    db.commit()
    db.refresh(challenge)
    return challenge


def challenge_form(db: Session, manager: User, challenge_id: int) -> dict:
    challenge = _owned_challenge(db, manager, challenge_id)
    content = challenge.content or {}
    return {"id": challenge.id, "title": challenge.title, "topic": challenge.topic, "scenario": challenge.scenario,
            "kind": challenge.kind or "quick", "options": list(challenge.options), "correct_index": challenge.correct_index,
            "steps": content.get("steps", []), "segments": content.get("segments", []),
            "feedback": challenge.feedback, "status": challenge.status}


# ---------- Asignaciones (HU-09) ----------

def assignable_items(db: Session, manager: User) -> list[dict]:
    """Contenido publicado de la empresa que puede asignarse."""
    modules = db.scalars(select(LearningModule).where(
        LearningModule.company_id == manager.company_id, LearningModule.status == "published").order_by(LearningModule.title)).all()
    challenges = db.scalars(select(Challenge).where(
        Challenge.company_id == manager.company_id, Challenge.status == "published").order_by(Challenge.title)).all()
    return ([{"item_type": "module", "item_id": m.id, "title": m.title, "topic": m.topic} for m in modules]
            + [{"item_type": "challenge", "item_id": c.id, "title": c.title, "topic": c.topic} for c in challenges])


def create_assignment(db: Session, manager: User, payload) -> Assignment:
    model = LearningModule if payload.item_type == "module" else Challenge
    item = db.get(model, payload.item_id)
    if not item or item.company_id != manager.company_id:
        raise NotFound("Contenido no encontrado")
    if item.status != "published":
        raise ContentError("Publica el contenido antes de asignarlo")
    if payload.target == "area":
        area = db.get(Area, payload.area_id)
        if not area or area.company_id != manager.company_id:
            raise NotFound("Área no encontrada")
    if payload.target == "user":
        worker = db.get(User, payload.user_id)
        if not worker or worker.company_id != manager.company_id or worker.role != "worker":
            raise NotFound("Trabajador no encontrado")
    if payload.due_at and _aware(payload.due_at) <= utcnow():
        raise ContentError("La fecha límite debe ser una fecha futura")
    assignment = Assignment(
        module_id=item.id if payload.item_type == "module" else None,
        challenge_id=item.id if payload.item_type == "challenge" else None,
        area_id=payload.area_id if payload.target == "area" else None,
        user_id=payload.user_id if payload.target == "user" else None,
        due_at=_aware(payload.due_at) if payload.due_at else None,
        created_by=manager.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def assignments_view(db: Session, manager: User) -> list[dict]:
    rows = db.scalars(select(Assignment).where(Assignment.created_by == manager.id)
                      .order_by(Assignment.assigned_at.desc(), Assignment.id.desc())).all()
    out = []
    for a in rows:
        if a.module_id is not None:
            item, kind = db.get(LearningModule, a.module_id), "module"
        else:
            item, kind = db.get(Challenge, a.challenge_id), "challenge"
        if item is None:
            continue
        if a.user_id is not None:
            worker = db.get(User, a.user_id)
            target = f"Trabajador: {worker.name}" if worker else "Trabajador eliminado"
        elif a.area_id is not None:
            area = db.get(Area, a.area_id)
            target = f"Área: {area.name}" if area else "Área eliminada"
        else:
            target = "Toda la empresa"
        out.append({"id": a.id, "item_type": kind, "item_id": item.id, "title": item.title,
                    "target": target, "due": visibility.due_label(a.due_at)})
    return out


def delete_assignment(db: Session, manager: User, assignment_id: int) -> None:
    assignment = db.get(Assignment, assignment_id)
    if not assignment or assignment.created_by != manager.id:
        raise NotFound("Asignación no encontrada")
    db.delete(assignment)
    db.commit()


# ---------- Estadísticas (HU-10) ----------

def stats(db: Session, manager: User) -> dict:
    """Desempeño por contenido y por trabajador, solo de lo que este gestor creó."""
    workers = progress_repository.active_workers(db, manager.company_id)
    modules = db.scalars(select(LearningModule).where(
        LearningModule.company_id == manager.company_id, LearningModule.created_by == manager.id)
        .order_by(LearningModule.updated_at.desc())).all()
    challenges = db.scalars(select(Challenge).where(
        Challenge.company_id == manager.company_id, Challenge.created_by == manager.id)
        .order_by(Challenge.updated_at.desc())).all()

    progress = {}
    if modules:
        for module_id, user_id, completed_at in db.execute(select(
                ModuleProgress.module_id, ModuleProgress.user_id, ModuleProgress.completed_at)
                .where(ModuleProgress.module_id.in_([m.id for m in modules]))).all():
            progress[(module_id, user_id)] = completed_at

    attempts = {}
    if challenges:
        for challenge_id, user_id, is_correct, tries in db.execute(select(
                ChallengeAttempt.challenge_id, ChallengeAttempt.user_id, ChallengeAttempt.is_correct, ChallengeAttempt.tries)
                .where(ChallengeAttempt.challenge_id.in_([c.id for c in challenges]))).all():
            attempts[(challenge_id, user_id)] = (is_correct, tries or 1)

    module_rows = []
    for m in modules:
        audience = visibility.audience(db, workers, "module", m.id)
        rows = []
        for w in audience:
            done = progress.get((m.id, w.id))
            rows.append({"user_id": w.id, "name": w.name, "area": w.area.name if w.area else "Sin área",
                         "completed": done is not None, "completed_at": done.isoformat() if done else None})
        completed = sum(1 for r in rows if r["completed"])
        module_rows.append({"id": m.id, "title": m.title, "topic": m.topic, "status": m.status,
                            "audience": len(audience), "completed": completed,
                            "completion_rate": rate(completed, len(audience)), "workers": rows})

    challenge_rows = []
    for c in challenges:
        audience = visibility.audience(db, workers, "challenge", c.id)
        rows, first_correct = [], 0
        for w in audience:
            attempt = attempts.get((c.id, w.id))
            if attempt:
                first_correct += attempt[0]
            # Solo participación: el gestor no ve si cada persona acertó.
            rows.append({"user_id": w.id, "name": w.name, "area": w.area.name if w.area else "Sin área",
                         "answered": attempt is not None, "tries": attempt[1] if attempt else 0})
        practiced = sum(1 for r in rows if r["answered"])
        visible_rate = practiced >= MIN_GROUP
        challenge_rows.append({"id": c.id, "title": c.title, "topic": c.topic, "status": c.status,
                               "kind": c.kind or "quick", "audience": len(audience), "attempts": practiced,
                               "correct": first_correct if visible_rate else None,
                               "success_rate": rate(first_correct, practiced) if visible_rate else None,
                               "workers": rows})

    certified = certificate_service.worker_certificate_count(db, manager.company_id)
    certificates = certificate_service.company_certificates(db, manager.company_id, workers)
    return {"modules": module_rows, "challenges": challenge_rows, "min_group": MIN_GROUP,
            "certificates": certificates,
            "workers": [{"user_id": w.id, "name": w.name, "area": w.area.name if w.area else "Sin área",
                         "certificates": certified.get(w.id, 0)} for w in workers],
            "topic_errors": topic_errors_for(db, manager.company_id, created_by=manager.id)}
