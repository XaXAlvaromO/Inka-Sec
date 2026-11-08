"""Reglas de progreso (simples y explícitas).

- Módulo: cuenta solo cuando el trabajador pulsa "Terminé" (completed_at). Sin avance parcial.
- Reto: se responde una sola vez; cuenta como correcto o incorrecto.
- % de módulos = módulos terminados / módulos publicados de la empresa.
- Retos: se reportan aparte (correctos / respondidos / total) para no mezclar peras con manzanas.
"""
from __future__ import annotations
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.models import User, ModuleProgress, utcnow
from app.models.challenge import Challenge, ChallengeAttempt
from app.repositories import progress_repository as repo
from app.repositories import module_repository


class NotFound(Exception): ...
class AlreadyAnswered(Exception): ...
class InvalidChoice(Exception): ...


def pct(part: int, total: int) -> int:
    return round(part * 100 / total) if total else 0


def rate(part: int, total: int) -> int | None:
    """Porcentaje o None cuando aún no hay datos (el front muestra '--')."""
    return round(part * 100 / total) if total else None


# ---------- Acciones del trabajador ----------

def mark_module_completed(db: Session, user: User, module_id: int) -> dict:
    if not module_repository.get_for_company(db, module_id, user.company_id, published_only=True):
        raise NotFound("Módulo no encontrado")
    p = db.scalar(select(ModuleProgress).where(ModuleProgress.user_id == user.id, ModuleProgress.module_id == module_id))
    if not p:
        p = ModuleProgress(user_id=user.id, module_id=module_id)
        db.add(p)
    if p.completed_at is None:          # idempotente: no se pisa la fecha original
        p.completed_at = utcnow()
        p.progress = 100
    try:
        db.commit()
    except IntegrityError:              # doble clic simultáneo: ya existe la fila
        db.rollback()
    return worker_progress(db, user)


def submit_challenge_answer(db: Session, user: User, challenge_id: int, choice: int) -> dict:
    ch = db.get(Challenge, challenge_id)
    if not ch or ch.company_id != user.company_id or ch.status != "published":
        raise NotFound("Reto no encontrado")
    if not 0 <= choice < len(ch.options):
        raise InvalidChoice("Opción fuera de rango")
    if repo.get_attempt(db, user.id, challenge_id):
        raise AlreadyAnswered("Ya respondiste este reto")
    correct = choice == ch.correct_index
    db.add(ChallengeAttempt(user_id=user.id, challenge_id=challenge_id, selected_index=choice, is_correct=correct))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AlreadyAnswered("Ya respondiste este reto")
    return {"is_correct": correct, "correct_index": ch.correct_index, "feedback": ch.feedback}


# ---------- Vista del trabajador ----------

def worker_progress(db: Session, user: User) -> dict:
    total_m = repo.count_published_modules(db, user.company_id)
    total_c = repo.count_published_challenges(db, user.company_id)
    done = repo.completed_modules_by_user(db, user.company_id, user.id).get(user.id, 0)
    answered, correct = repo.challenge_results_by_user(db, user.company_id, user.id).get(user.id, (0, 0))
    return {
        "modules": {"completed": done, "total": total_m, "percent": pct(done, total_m)},
        "challenges": {"correct": correct, "answered": answered, "total": total_c,
                       "accuracy": rate(correct, answered)},
        "weak_topics": [{"topic": t, "errors": int(e)} for t, _, e in
                        repo.topic_errors(db, user.company_id, user_id=user.id)],
    }


# ---------- Vista de la empresa (admin) ----------

def company_progress(db: Session, company_id: int) -> list[dict]:
    """Una fila por trabajador activo. Base del dashboard del administrador."""
    total_m = repo.count_published_modules(db, company_id)
    total_c = repo.count_published_challenges(db, company_id)
    done = repo.completed_modules_by_user(db, company_id)
    results = repo.challenge_results_by_user(db, company_id)
    rows = []
    for u in repo.active_workers(db, company_id):
        c = done.get(u.id, 0)
        answered, correct = results.get(u.id, (0, 0))
        rows.append({
            "user_id": u.id, "name": u.name, "email": u.email,
            "area": u.area.name if u.area else "Sin área",
            "modules_completed": c, "modules_total": total_m, "modules_percent": pct(c, total_m),
            "challenges_answered": answered, "challenges_correct": correct, "challenges_total": total_c,
            "challenges_accuracy": rate(correct, answered),
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    done = sum(r["modules_completed"] for r in rows)
    possible = sum(r["modules_total"] for r in rows)
    answered = sum(r["challenges_answered"] for r in rows)
    correct = sum(r["challenges_correct"] for r in rows)
    return {"workers": len(rows), "modules_percent": pct(done, possible),
            "challenges_answered": answered, "challenges_correct": correct,
            "challenges_accuracy": rate(correct, answered)}


def by_area(rows: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["area"]].append(r)
    return {name: summarize(items) for name, items in groups.items()}


# ---------- Vista del gestor ----------

def manager_stats(db: Session, manager: User) -> dict:
    """Desempeño solo de lo que este gestor creó."""
    workers = len(repo.active_workers(db, manager.company_id))
    return {
        "modules": [{"id": m.id, "title": m.title, "topic": m.topic, "status": m.status,
                     "completed": n, "total_workers": workers, "completion_rate": rate(n, workers)}
                    for m, n in repo.module_completion(db, manager.company_id, created_by=manager.id)],
        "challenges": [{"id": c.id, "title": c.title, "topic": c.topic, "status": c.status,
                        "attempts": int(a), "correct": int(ok), "success_rate": rate(int(ok), int(a))}
                       for c, a, ok in repo.challenge_performance(db, manager.company_id, created_by=manager.id)],
        "topic_errors": _topic_errors(db, manager.company_id, created_by=manager.id),
    }


def _topic_errors(db: Session, company_id: int, created_by: int | None = None) -> list[dict]:
    return [{"topic": t, "attempts": int(a), "errors": int(e), "error_rate": rate(int(e), int(a))}
            for t, a, e in repo.topic_errors(db, company_id, created_by=created_by)]
