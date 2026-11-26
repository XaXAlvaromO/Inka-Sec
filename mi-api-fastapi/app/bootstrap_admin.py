import re
from sqlalchemy import select
from app.db.session import SessionLocal, Base, engine
from app.core.constants import PLATFORM_COMPANY_NAME, PLATFORM_COMPANY_SLUG
from app.models.models import Company, Area, User
from app.core.config import settings
from app.core.security import hash_password
from app.repositories.user_repository import get_by_email, normalize_email
from app.schemas.user import EMAIL_PATTERN

MIN_ADMIN_PASSWORD_LENGTH = 12

def _validate_credentials(email: str | None, password: str | None, *, label: str):
    if not email or not password:
        raise SystemExit(f"Configura {label}_EMAIL y {label}_PASSWORD")
    if not re.fullmatch(EMAIL_PATTERN, email.strip()):
        raise SystemExit(f"{label}_EMAIL no es un correo válido")
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise SystemExit(f"{label}_PASSWORD debe tener al menos {MIN_ADMIN_PASSWORD_LENGTH} caracteres")

def validate_bootstrap_settings():
    """Falla antes de tocar la base de datos si la configuración del admin inicial es débil."""
    _validate_credentials(settings.bootstrap_admin_email, settings.bootstrap_admin_password, label="BOOTSTRAP_ADMIN")

def _bootstrap_superadmin(db):
    """Crea la cuenta de superadministrador, dueña de toda la plataforma (todas las empresas).

    Es opcional a propósito: si BOOTSTRAP_SUPERADMIN_EMAIL/PASSWORD no están configuradas, no
    se crea nada y el resto del script sigue igual que antes de esta función existir.
    """
    email, password = settings.bootstrap_superadmin_email, settings.bootstrap_superadmin_password
    if not email and not password:
        return
    _validate_credentials(email, password, label="BOOTSTRAP_SUPERADMIN")
    if get_by_email(db, email):
        print("Superadministrador ya existe; no se modifica.")
        return
    company = db.scalar(select(Company).where(Company.slug == PLATFORM_COMPANY_SLUG))
    if not company:
        company = Company(name=PLATFORM_COMPANY_NAME, slug=PLATFORM_COMPANY_SLUG)
        db.add(company); db.commit(); db.refresh(company)
    superadmin = User(company_id=company.id, area_id=None, name="Superadministrador",
                       email=normalize_email(email), password_hash=hash_password(password),
                       role="superadmin", is_active=True)
    db.add(superadmin); db.commit()
    print("Superadministrador creado.")

def main():
    validate_bootstrap_settings()
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        if get_by_email(db,settings.bootstrap_admin_email):
            print("Bootstrap admin ya existe; no se modifica.")
        else:
            company=db.scalar(select(Company).where(Company.name==settings.bootstrap_company_name))
            if not company:
                company=Company(name=settings.bootstrap_company_name,slug=settings.bootstrap_company_name.lower().replace(" ","-")[:80]); db.add(company); db.commit(); db.refresh(company)
            area=db.scalar(select(Area).where(Area.company_id==company.id,Area.name=="Tecnología"))
            if not area:
                area=Area(company_id=company.id,name="Tecnología"); db.add(area); db.commit(); db.refresh(area)
            admin=User(company_id=company.id,area_id=area.id,name="Administrador inicial",email=normalize_email(settings.bootstrap_admin_email),password_hash=hash_password(settings.bootstrap_admin_password),role="admin",is_active=True)
            db.add(admin); db.commit(); print("Administrador inicial creado.")
        _bootstrap_superadmin(db)
    finally:
        db.close()

if __name__=="__main__": main()
