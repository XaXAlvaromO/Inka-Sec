from sqlalchemy import select

from app.core.config import settings
from app.core.security import totp_code
from app.db.session import SessionLocal
from app.models.models import User


def main(email: str):
    if settings.app_env.lower() == "production":
        raise SystemExit("dev_totp está deshabilitado en producción")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower().strip()))
        if not user:
            raise SystemExit("Usuario no encontrado")
        if not user.totp_secret:
            raise SystemExit("El usuario no tiene TOTP configurado")
        print(totp_code(user.totp_secret))
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m app.dev_totp correo@empresa.pe")
    main(sys.argv[1])
