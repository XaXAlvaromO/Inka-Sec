from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.constants import PLATFORM_COMPANY_NAME, PLATFORM_COMPANY_SLUG
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.services.starter_content import ensure_starter_modules
from app.demo_challenges import ensure_demo_challenges
from app.models.models import Area, Company, Notification, User


def seed_demo():
    # Se puede ejecutar a mano (python -m app.seed) aunque SEED_DEMO_DATA sea false:
    # en producción crearía cuentas con correos conocidos y una contraseña compartida.
    if settings.is_production:
        raise RuntimeError("seed_demo está deshabilitado en producción")
    if not settings.demo_password:
        raise RuntimeError(
            "SEED_DEMO_DATA=true requiere DEMO_PASSWORD en backend/.env. "
            "Usa una contraseña solo para desarrollo local."
        )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        company = db.scalar(select(Company).where(Company.slug == "inkasec-demo"))
        if not company:
            company = Company(name="InkaSec Demo", slug="inkasec-demo")
            db.add(company)
            db.commit()
            db.refresh(company)

        areas = {}
        for name in ["Finanzas", "Tecnología", "RR. HH.", "Ventas", "Logística"]:
            area = db.scalar(
                select(Area).where(Area.company_id == company.id, Area.name == name)
            )
            if not area:
                area = Area(company_id=company.id, name=name)
                db.add(area)
                db.commit()
                db.refresh(area)
            areas[name] = area

        demo = [
            ("María López", "trabajador@inkasec.pe", "worker", "Finanzas"),
            ("Lucía Torres", "gestor@inkasec.pe", "manager", "RR. HH."),
            ("Diego Vargas", "admin@inkasec.pe", "admin", "Tecnología"),
        ]
        users = {}
        for name, email, role, area_name in demo:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    company_id=company.id,
                    area_id=areas[area_name].id,
                    name=name,
                    email=email,
                    password_hash=hash_password(settings.demo_password),
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            users[role] = user

        # Cuenta de superadministrador, en su propia empresa interna (no "InkaSec Demo"): así
        # el panel de superadministrador tiene, desde el primer arranque, al menos una empresa
        # cliente real que gestionar, separada de la plataforma como en producción.
        platform = db.scalar(select(Company).where(Company.slug == PLATFORM_COMPANY_SLUG))
        if not platform:
            platform = Company(name=PLATFORM_COMPANY_NAME, slug=PLATFORM_COMPANY_SLUG)
            db.add(platform)
            db.commit()
            db.refresh(platform)
        if not db.scalar(select(User).where(User.email == "superadmin@inkasec.pe")):
            db.add(
                User(
                    company_id=platform.id,
                    area_id=None,
                    name="Admin Plataforma",
                    email="superadmin@inkasec.pe",
                    password_hash=hash_password(settings.demo_password),
                    role="superadmin",
                    is_active=True,
                )
            )
            db.commit()

        # Los mismos módulos COM-B de ejemplo y retos de demostración que recibe, de forma
        # automática, el primer gestor de cualquier empresa nueva (ver app/services/starter_content.py).
        ensure_starter_modules(db, company, users["manager"])
        ensure_demo_challenges(db, company, users["manager"])

        if not db.scalar(select(Notification).where(Notification.user_id == users["worker"].id)):
            db.add(
                Notification(
                    user_id=users["worker"].id,
                    title="Ruta de aprendizaje disponible",
                    body="Tienes 7 módulos COM-B asignados.",
                    scheduled_for=datetime.now(timezone.utc),
                )
            )
        db.commit()

        print("Demo local seeded.")
        print("worker: trabajador@inkasec.pe")
        print("manager: gestor@inkasec.pe")
        print("admin: admin@inkasec.pe")
        print("superadmin: superadmin@inkasec.pe")
        print("La contraseña es la configurada en DEMO_PASSWORD; no se imprime en logs.")
        print("Gestor y administrador piden código 2FA por correo: con EMAIL_BACKEND=console aparece en esta terminal.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
