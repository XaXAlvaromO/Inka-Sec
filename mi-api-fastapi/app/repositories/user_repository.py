from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.models import User

def normalize_email(email: str) -> str:
    return email.lower().strip()

def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))

def list_by_company(db: Session, company_id: int) -> list[User]:
    return list(db.scalars(select(User).where(User.company_id == company_id).order_by(User.id)).all())

def count_by_company(db: Session, company_id: int) -> int:
    return int(db.scalar(select(func.count(User.id)).where(User.company_id == company_id)) or 0)
