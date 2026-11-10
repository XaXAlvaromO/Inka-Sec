from app.core.config import settings
from app.core.security import totp_code
from app.db.session import SessionLocal
from app.repositories.user_repository import get_by_email


def main(email: str):
    if settings.is_production:
        raise SystemExit("dev_totp está deshabilitado en producción")

    db = SessionLocal()
    try:
        user = get_by_email(db, email)
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
