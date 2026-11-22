"""Crea los retos demo para el trabajador. SOLO para desarrollo. Es idempotente.

Uso:  python -m app.dev_seed_challenges
(Con SEED_DEMO_DATA=true ya se crean al arrancar la API.)
"""
from sqlalchemy import select
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app import models  # noqa: F401  (registra las tablas)
from app.demo_challenges import DEMO_CHALLENGES, ensure_demo_challenges
from app.models.models import Company, User


def main():
    if settings.is_production:
        raise SystemExit("Deshabilitado en producción")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        company = db.scalar(select(Company).where(Company.slug == "inkasec-demo"))
        manager = db.scalar(select(User).where(User.email == "gestor@inkasec.pe"))
        if not company or not manager:
            raise SystemExit("Primero corre el seed demo (SEED_DEMO_DATA=true y reinicia la API).")
        created = ensure_demo_challenges(db, company, manager)
        print(f"Retos creados: {created} (ya existían: {len(DEMO_CHALLENGES) - created})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
