"""Reglas de progreso (simples y explícitas).

- Módulo: cuenta solo cuando el trabajador pulsa "Terminé" (completed_at). Sin avance parcial.
- Reto: entrena, no califica. Se puede repetir sin límite; el primer intento queda para las
  estadísticas agregadas del tema y la práctica posterior solo la ve el propio trabajador.
- Preguntas de capacidad del módulo: se guarda el mejor porcentaje (cuenta para el certificado).
- % de módulos = módulos terminados / módulos publicados de la empresa.
- Retos: se reportan aparte (correctos / respondidos / total) para no mezclar peras con manzanas.
"""
from __future__ import annotations
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.models import User, ModuleProgress, Reflection, utcnow
from app.models.challenge import Challenge, ChallengeAttempt
from app.repositories import progress_repository as repo
from app.repositories import module_repository
from app.services import visibility, certificate_service, challenge_service


class NotFound(Exception): ...
class InvalidChoice(Exception): ...


def visible_module(db: Session, user: User, module_id: int):
    """Módulo publicado de la empresa que este trabajador puede abrir (asignado o para todos)."""
    module = module_repository.get_for_company(db, module_id, user.company_id, published_only=True)
    if not module or not visibility.can_open(db, user, "module", module.id)[0]:
        raise NotFound("Módulo no encontrado")
    return module


def pct(part: int, total: int) -> int:
    return round(part * 100 / total) if total else 0


def rate(part: int, total: int) -> int | None:
    """Porcentaje o None cuando aún no hay datos (el front muestra '--')."""
    return round(part * 100 / total) if total else None


# ---------- Acciones del trabajador ----------

def mark_module_completed(db: Session, user: User, module_id: int) -> dict:
    visible_module(db, user, module_id)
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
    new = certificate_service.sync(db, user)
    return {**worker_progress(db, user), "new_certificates": [c.topic for c in new]}


def _visible_challenge(db: Session, user: User, challenge_id: int) -> Challenge:
    ch = db.get(Challenge, challenge_id)
    if not ch or ch.company_id != user.company_id or ch.status != "published":
        raise NotFound("Reto no encontrado")
    if not visibility.can_open(db, user, "challenge", ch.id)[0]:
        raise NotFound("Reto no encontrado")
    return ch


def check_challenge_step(db: Session, user: User, challenge_id: int, step: int, choice: int) -> dict:
    ch = _visible_challenge(db, user, challenge_id)
    try:
        return challenge_service.check_step(ch, step, choice)
    except challenge_service.InvalidAnswer as e:
        raise InvalidChoice(str(e))


def submit_challenge_answer(db: Session, user: User, challenge_id: int, choice: int | None = None,
                            choices: list[int] | None = None, marked: list[int] | None = None) -> dict:
    ch = _visible_challenge(db, user, challenge_id)
    try:
        result = challenge_service.grade(ch, choice=choice, choices=choices, marked=marked)
    except challenge_service.InvalidAnswer as e:
        raise InvalidChoice(str(e))
    attempt = repo.get_attempt(db, user.id, challenge_id)
    if attempt is None:
        attempt = ChallengeAttempt(user_id=user.id, challenge_id=challenge_id, selected_index=result["selected_index"],
                                   is_correct=result["is_correct"], tries=0)
        db.add(attempt)
    # El primer intento no se pisa nunca; la práctica solo actualiza lo que ve el trabajador.
    tries = (attempt.tries or 0) + 1
    attempt.tries = tries
    attempt.last_correct = result["is_correct"]
    attempt.last_score = result["score"]
    try:
        db.commit()
    except IntegrityError:              # doble envío simultáneo: se cuenta como un intento
        db.rollback()
    result.pop("selected_index", None)
    return {**result, "tries": tries}


# ---------- Vista del trabajador ----------

def worker_progress(db: Session, user: User) -> dict:
    # Solo cuentan los módulos y retos que este trabajador tiene asignados o son para toda la empresa.
    visible_m = visibility.visible_items(db, user, "module")
    visible_c = visibility.visible_items(db, user, "challenge")
    done_ids = set(db.scalars(select(ModuleProgress.module_id).where(
        ModuleProgress.user_id == user.id, ModuleProgress.completed_at.is_not(None))).all())
    total_m, total_c = len(visible_m), len(visible_c)
    done = len(done_ids & set(visible_m))
    answered, correct = repo.own_challenge_practice(db, user.company_id, user.id)
    return {
        "modules": {"completed": done, "total": total_m, "percent": pct(done, total_m)},
        "challenges": {"correct": correct, "answered": answered, "total": total_c,
                       "accuracy": rate(correct, answered)},
        "weak_topics": [{"topic": t, "errors": int(e), "attempts": int(a), "score": pct(int(a) - int(e), int(a))}
                        for t, a, e in repo.topic_errors(db, user.company_id, user_id=user.id)],
    }


# ---------- Vista de la empresa (admin) ----------

def company_progress(db: Session, company_id: int) -> list[dict]:
    """Una fila por trabajador activo. Base del dashboard del administrador.

    Los retos solo aportan participación: nadie fuera del trabajador ve sus aciertos o errores.
    """
    total_m = repo.count_published_modules(db, company_id)
    total_c = repo.count_published_challenges(db, company_id)
    done = repo.completed_modules_by_user(db, company_id)
    results = repo.challenge_results_by_user(db, company_id)
    rows = []
    for u in repo.active_workers(db, company_id):
        c = done.get(u.id, 0)
        answered, _ = results.get(u.id, (0, 0))
        rows.append({
            "user_id": u.id, "name": u.name, "email": u.email,
            "area": u.area.name if u.area else "Sin área",
            "modules_completed": c, "modules_total": total_m, "modules_percent": pct(c, total_m),
            "challenges_practiced": answered, "challenges_total": total_c,
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    done = sum(r["modules_completed"] for r in rows)
    possible = sum(r["modules_total"] for r in rows)
    return {"workers": len(rows), "modules_percent": pct(done, possible),
            "challenges_practiced": sum(r["challenges_practiced"] for r in rows)}


def by_area(rows: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["area"]].append(r)
    return {name: summarize(items) for name, items in groups.items()}


# ---------- Vista del gestor ----------

MIN_GROUP = 3  # con menos personas, un porcentaje "agregado" delataría a alguien


def topic_errors_for(db: Session, company_id: int, created_by: int | None = None) -> list[dict]:
    """Temas con más errores en el primer intento (retos publicados), sin nombres.

    Solo aparecen temas practicados por al menos MIN_GROUP personas distintas.
    Con created_by, solo los retos de ese gestor.
    """
    return [{"topic": t, "attempts": int(a), "errors": int(e), "error_rate": rate(int(e), int(a)), "people": int(n)}
            for t, a, e, n in repo.topic_errors(db, company_id, created_by=created_by, with_people=True)
            if int(n) >= MIN_GROUP]


# ---------- Contenido del módulo para el trabajador ----------

def worker_module_view(content: dict) -> dict:
    """El trabajador ve el módulo sin las respuestas correctas: se califican en el servidor."""
    view = dict(content)
    view["capacity_questions"] = [
        {"prompt": q.get("prompt", ""), "options": list(q.get("options", []))}
        for q in content.get("capacity_questions", [])
    ]
    return view


def grade_capacity(db: Session, user: User, module_id: int, answers: list[dict]) -> dict:
    module = visible_module(db, user, module_id)
    questions = module.content_json.get("capacity_questions", [])
    if len(answers) != len(questions) or sorted(a["index"] for a in answers) != list(range(len(questions))):
        raise InvalidChoice("Responde todas las preguntas del módulo")
    by_index = {a["index"]: a["choice"] for a in answers}
    results = []
    for index, q in enumerate(questions):
        options = q.get("options", [])
        choice = by_index[index]
        if not 0 <= choice < len(options):
            raise InvalidChoice("Opción fuera de rango")
        correct = choice == q.get("correct")
        results.append({"index": index, "is_correct": correct, "correct_index": q.get("correct"),
                        "feedback": q.get("feedback", "")})
    correct = sum(r["is_correct"] for r in results)
    percent = pct(correct, len(results))
    progress = db.scalar(select(ModuleProgress).where(ModuleProgress.user_id == user.id, ModuleProgress.module_id == module_id))
    if not progress:
        progress = ModuleProgress(user_id=user.id, module_id=module_id, progress=0)
        db.add(progress)
    progress.score = max(progress.score or 0, percent)   # se guarda el mejor intento: repetir no castiga
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    new = certificate_service.sync(db, user)   # si ya había completado el módulo, puede ganar el certificado aquí
    return {"results": results, "correct": correct, "total": len(results), "percent": percent,
            "pass_percent": certificate_service.PASS_PERCENT, "new_certificates": [c.topic for c in new]}


def save_reflections(db: Session, user: User, module_id: int, responses: list[dict]) -> int:
    visible_module(db, user, module_id)
    for item in responses:
        row = db.scalar(select(Reflection).where(Reflection.user_id == user.id, Reflection.module_id == module_id,
                                                 Reflection.prompt_code == item["prompt_code"]))
        if row:
            row.text = item["text"].strip()
        else:
            db.add(Reflection(user_id=user.id, module_id=module_id, prompt_code=item["prompt_code"], text=item["text"].strip()))
    db.commit()
    return len(responses)


def saved_reflections(db: Session, user: User, module_id: int) -> dict[str, str]:
    rows = db.scalars(select(Reflection).where(Reflection.user_id == user.id, Reflection.module_id == module_id)).all()
    return {r.prompt_code: r.text for r in rows}
