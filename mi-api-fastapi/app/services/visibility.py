"""Quién ve cada módulo y reto (HU-09).

Regla:
- Un contenido publicado SIN asignaciones es visible para todos los trabajadores de la empresa.
- Un contenido CON asignaciones solo lo ven los trabajadores alcanzados por alguna de ellas:
  toda la empresa, un área o una persona concreta.
- Si varias asignaciones alcanzan a un trabajador, la fecha límite que cuenta es la más cercana.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge
from app.models.models import Assignment, LearningModule, User, utcnow

KINDS = {
    "module": (LearningModule, Assignment.module_id),
    "challenge": (Challenge, Assignment.challenge_id),
}


def aware(value: datetime | None) -> datetime | None:
    """SQLite devuelve fechas sin zona horaria; las tratamos como UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def rules_by_item(db: Session, kind: str, item_ids: list[int]) -> dict[int, list[tuple]]:
    """{item_id: [(user_id, area_id, due_at), ...]} solo para los ids indicados."""
    rules: dict[int, list[tuple]] = defaultdict(list)
    if not item_ids:
        return rules
    _, column = KINDS[kind]
    rows = db.execute(
        select(column, Assignment.user_id, Assignment.area_id, Assignment.due_at).where(column.in_(item_ids))
    ).all()
    for item_id, user_id, area_id, due in rows:
        rules[item_id].append((user_id, area_id, aware(due)))
    return rules


def _applies(rule: tuple, worker_id: int, area_id: int | None) -> bool:
    user_id, rule_area, _ = rule
    if user_id is not None:
        return user_id == worker_id
    if rule_area is not None:
        return rule_area == area_id
    return True  # sin persona ni área: toda la empresa


def access(rules: list[tuple], worker_id: int, area_id: int | None) -> tuple[bool, datetime | None]:
    """(puede verlo, fecha límite). Sin reglas el contenido es visible para todos y sin fecha."""
    if not rules:
        return True, None
    matched = [rule for rule in rules if _applies(rule, worker_id, area_id)]
    if not matched:
        return False, None
    dues = [rule[2] for rule in matched if rule[2] is not None]
    return True, (min(dues) if dues else None)


def visible_items(db: Session, worker: User, kind: str) -> dict[int, datetime | None]:
    """{id: fecha_límite} de los contenidos publicados que este trabajador puede abrir."""
    model, _ = KINDS[kind]
    ids = list(db.scalars(select(model.id).where(model.company_id == worker.company_id, model.status == "published")).all())
    rules = rules_by_item(db, kind, ids)
    visible: dict[int, datetime | None] = {}
    for item_id in ids:
        ok, due = access(rules.get(item_id, []), worker.id, worker.area_id)
        if ok:
            visible[item_id] = due
    return visible


def can_open(db: Session, worker: User, kind: str, item_id: int) -> tuple[bool, datetime | None]:
    rules = rules_by_item(db, kind, [item_id]).get(item_id, [])
    return access(rules, worker.id, worker.area_id)


def audience(db: Session, workers: list[User], kind: str, item_id: int) -> list[User]:
    """Trabajadores activos a quienes les toca este contenido."""
    rules = rules_by_item(db, kind, [item_id]).get(item_id, [])
    return [w for w in workers if access(rules, w.id, w.area_id)[0]]


def due_label(due: datetime | None) -> str:
    if due is None:
        return "Sin fecha límite"
    stamp = aware(due)
    prefix = "Venció el" if stamp < utcnow() else "Vence el"
    return f"{prefix} {stamp:%d/%m/%Y}"
