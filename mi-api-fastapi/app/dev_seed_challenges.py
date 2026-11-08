"""Crea retos de ejemplo SOLO para desarrollo (empresa demo). Es idempotente.

Uso:  python -m app.dev_seed_challenges
"""
from sqlalchemy import select
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app import models  # noqa: F401  (registra las tablas)
from app.models.models import Company, User
from app.models.challenge import Challenge

DEMO = [
    ("Correo del 'gerente' pidiendo una transferencia urgente", "Phishing",
     "Recibes un correo del gerente general desde una dirección parecida a la suya: pide una transferencia urgente y que no avises a nadie. ¿Qué haces?",
     ["Hago la transferencia, es el gerente", "Verifico por otro canal (llamada o chat oficial) antes de hacer nada", "Respondo al correo pidiendo confirmar", "Reenvío el correo a mis compañeros"], 1,
     "Verifica siempre por un canal distinto al del mensaje sospechoso."),
    ("Mensaje de 'soporte' que pide tu contraseña", "Credenciales",
     "Alguien que dice ser de soporte técnico te escribe por WhatsApp y te pide tu contraseña para 'actualizar tu cuenta'. ¿Qué haces?",
     ["Se la doy, es soporte", "Solo le doy los primeros caracteres", "No la comparto y aviso al área de seguridad", "Cambio mi contraseña y se la envío"], 2,
     "Nadie legítimo te pedirá tu contraseña. Repórtalo."),
    ("USB encontrado en el estacionamiento", "Dispositivos",
     "Encuentras una USB en el estacionamiento de la oficina. ¿Qué haces?",
     ["La conecto para ver de quién es", "La conecto en una laptop vieja", "No la conecto y la entrego al área de TI", "La uso, parece nueva"], 2,
     "Una USB desconocida puede instalar malware al conectarla."),
]


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
        created = 0
        for title, topic, scenario, options, correct, feedback in DEMO:
            if db.scalar(select(Challenge).where(Challenge.company_id == company.id, Challenge.title == title)):
                continue
            db.add(Challenge(company_id=company.id, title=title, topic=topic, scenario=scenario, options=options,
                             correct_index=correct, feedback=feedback, status="published", created_by=manager.id))
            created += 1
        db.commit()
        print(f"Retos creados: {created} (ya existían: {len(DEMO) - created})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
