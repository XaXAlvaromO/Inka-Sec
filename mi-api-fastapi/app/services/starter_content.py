"""Contenido inicial para una empresa recién creada.

Cuando el administrador crea al primer gestor de su empresa y todavía no hay ningún
módulo ni reto propio, se precargan los módulos COM-B de ejemplo (app/data/modules_com_b.json)
y los retos de demostración, ya publicados, para que el gestor no empiece de cero y los
trabajadores tengan algo que hacer desde el primer día. Es idempotente: si la empresa ya
tiene contenido propio (de este u otro gestor), no se toca nada.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.demo_challenges import ensure_demo_challenges
from app.models.challenge import Challenge
from app.models.models import Company, LearningModule, User

MODULES_PATH = Path(__file__).resolve().parent.parent / "data" / "modules_com_b.json"


def _has_own_content(db, company_id: int) -> bool:
    if db.scalar(select(LearningModule.id).where(LearningModule.company_id == company_id)):
        return True
    if db.scalar(select(Challenge.id).where(Challenge.company_id == company_id)):
        return True
    return False


def ensure_starter_modules(db, company: Company, manager: User) -> int:
    """Crea los módulos COM-B de ejemplo que falten en esta empresa. Devuelve cuántos creó."""
    created = 0
    payloads = json.loads(MODULES_PATH.read_text(encoding="utf-8"))
    for payload in payloads:
        exists = db.scalar(select(LearningModule.id).where(
            LearningModule.company_id == company.id, LearningModule.slug == payload["slug"]))
        if exists:
            continue
        module = LearningModule(
            company_id=company.id, slug=payload["slug"], title=payload["title"], topic=payload["topic"],
            behavior_objective=payload["behavior_objective"], status="published",
            content_json=payload, created_by=manager.id,
        )
        db.add(module)
        db.commit()
        db.refresh(module)
        created += 1
    return created


def seed_starter_content_if_empty(db, company: Company, manager: User) -> dict:
    """Si la empresa todavía no tiene ningún módulo ni reto propio, precarga el contenido
    inicial (módulos COM-B de ejemplo + retos de demostración) atribuido al gestor recién
    creado. No hace nada si la empresa ya tiene contenido."""
    if _has_own_content(db, company.id):
        return {"modules": 0, "challenges": 0}
    modules_created = ensure_starter_modules(db, company, manager)
    challenges_created = ensure_demo_challenges(db, company, manager)
    return {"modules": modules_created, "challenges": challenges_created}
