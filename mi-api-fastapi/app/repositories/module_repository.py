from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.models import LearningModule

def list_published(db: Session, company_id: int) -> list[LearningModule]:
    return list(db.scalars(select(LearningModule).where(LearningModule.company_id == company_id, LearningModule.status == "published").order_by(LearningModule.id)).all())

def list_all(db: Session, company_id: int) -> list[LearningModule]:
    return list(db.scalars(select(LearningModule).where(LearningModule.company_id == company_id).order_by(LearningModule.updated_at.desc())).all())

def get_for_company(db: Session, module_id: int, company_id: int, *, published_only: bool = False) -> LearningModule | None:
    """Devuelve el módulo solo si pertenece a la empresa (y está publicado, si se pide)."""
    row = db.get(LearningModule, module_id)
    if not row or row.company_id != company_id:
        return None
    if published_only and row.status != "published":
        return None
    return row
