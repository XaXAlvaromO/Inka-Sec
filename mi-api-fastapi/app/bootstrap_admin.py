import re
from sqlalchemy import select
from app.db.session import SessionLocal, Base, engine
from app.models.models import Company, Area, User
from app.core.config import settings
from app.core.security import hash_password, is_valid_totp_secret
from app.repositories.user_repository import get_by_email, normalize_email
from app.schemas.user import EMAIL_PATTERN

MIN_ADMIN_PASSWORD_LENGTH = 12

def validate_bootstrap_settings():
    """Falla antes de tocar la base de datos si la configuración del admin inicial es débil."""
    email, password, secret = settings.bootstrap_admin_email, settings.bootstrap_admin_password, settings.bootstrap_admin_totp_secret
    if not email or not password or not secret:
        raise SystemExit("Configura BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD y BOOTSTRAP_ADMIN_TOTP_SECRET")
    if not re.fullmatch(EMAIL_PATTERN, email.strip()):
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL no es un correo válido")
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise SystemExit(f"BOOTSTRAP_ADMIN_PASSWORD debe tener al menos {MIN_ADMIN_PASSWORD_LENGTH} caracteres")
    if not is_valid_totp_secret(secret):
        raise SystemExit("BOOTSTRAP_ADMIN_TOTP_SECRET debe ser un secreto Base32 válido de al menos 16 caracteres")

def main():
    validate_bootstrap_settings()
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:
        if get_by_email(db,settings.bootstrap_admin_email):
            print("Bootstrap admin ya existe; no se modifica."); return
        company=db.scalar(select(Company).where(Company.name==settings.bootstrap_company_name))
        if not company:
            company=Company(name=settings.bootstrap_company_name,slug=settings.bootstrap_company_name.lower().replace(" ","-")[:80]); db.add(company); db.commit(); db.refresh(company)
        area=db.scalar(select(Area).where(Area.company_id==company.id,Area.name=="Tecnología"))
        if not area:
            area=Area(company_id=company.id,name="Tecnología"); db.add(area); db.commit(); db.refresh(area)
        admin=User(company_id=company.id,area_id=area.id,name="Administrador inicial",email=normalize_email(settings.bootstrap_admin_email),password_hash=hash_password(settings.bootstrap_admin_password),role="admin",totp_secret=settings.bootstrap_admin_totp_secret.strip(),is_active=True)
        db.add(admin); db.commit(); print("Administrador inicial creado.")
    finally:
        db.close()

if __name__=="__main__": main()
