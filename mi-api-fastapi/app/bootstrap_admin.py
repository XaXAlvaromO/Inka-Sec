from sqlalchemy import select
from app.db.session import SessionLocal, Base, engine
from app.models.models import Company, Area, User
from app.core.config import settings
from app.core.security import hash_password

def main():
    Base.metadata.create_all(bind=engine)
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password or not settings.bootstrap_admin_totp_secret:
        raise SystemExit("Configura BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_PASSWORD y BOOTSTRAP_ADMIN_TOTP_SECRET")
    db=SessionLocal()
    try:
        existing=db.scalar(select(User).where(User.email==settings.bootstrap_admin_email.lower().strip()))
        if existing:
            print("Bootstrap admin ya existe; no se modifica."); return
        company=db.scalar(select(Company).where(Company.name==settings.bootstrap_company_name))
        if not company:
            company=Company(name=settings.bootstrap_company_name,slug=settings.bootstrap_company_name.lower().replace(" ","-")[:80]); db.add(company); db.commit(); db.refresh(company)
        area=db.scalar(select(Area).where(Area.company_id==company.id,Area.name=="Tecnología"))
        if not area:
            area=Area(company_id=company.id,name="Tecnología"); db.add(area); db.commit(); db.refresh(area)
        admin=User(company_id=company.id,area_id=area.id,name="Administrador inicial",email=settings.bootstrap_admin_email.lower().strip(),password_hash=hash_password(settings.bootstrap_admin_password),role="admin",totp_secret=settings.bootstrap_admin_totp_secret,is_active=True)
        db.add(admin); db.commit(); print("Administrador inicial creado.")
    finally:
        db.close()

if __name__=="__main__": main()
