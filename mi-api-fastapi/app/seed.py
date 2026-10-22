from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, new_totp_secret
from app.db.session import Base, SessionLocal, engine
from app.models.models import Area, Company, LearningModule, ModuleProgress, Notification, User


def seed_demo():
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
                secret = new_totp_secret() if role in {"manager", "admin"} else None
                user = User(
                    company_id=company.id,
                    area_id=areas[area_name].id,
                    name=name,
                    email=email,
                    password_hash=hash_password(settings.demo_password),
                    role=role,
                    totp_secret=secret,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            users[role] = user

        path = Path(__file__).parent / "data" / "modules_com_b.json"
        for payload in json.loads(path.read_text(encoding="utf-8")):
            module = db.scalar(
                select(LearningModule).where(
                    LearningModule.company_id == company.id,
                    LearningModule.slug == payload["slug"],
                )
            )
            if not module:
                module = LearningModule(
                    company_id=company.id,
                    slug=payload["slug"],
                    title=payload["title"],
                    topic=payload["topic"],
                    behavior_objective=payload["behavior_objective"],
                    status="published",
                    content_json=payload,
                    created_by=users["manager"].id,
                )
                db.add(module)
                db.commit()
                db.refresh(module)
                db.add(ModuleProgress(user_id=users["worker"].id, module_id=module.id, progress=0))

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
        print("La contraseña es la configurada en DEMO_PASSWORD; no se imprime en logs.")
        print("Para un TOTP local usa: python -m app.dev_totp <correo>")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
