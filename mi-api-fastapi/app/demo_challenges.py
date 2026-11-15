"""Los dos retos de demostración para el trabajador. Se usan en el seed demo y en dev_seed_challenges.

Son idempotentes: si un reto ya existe (mismo título en la empresa), no se duplica.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge
from app.models.models import Company, User

DEMO_CHALLENGES = [
    {
        "title": "Correo del 'gerente' pidiendo una transferencia urgente",
        "topic": "Phishing",
        "scenario": "Recibes un correo del gerente general desde una dirección parecida a la suya: pide una transferencia urgente y que no avises a nadie. ¿Qué haces?",
        "options": ["Hago la transferencia, es el gerente", "Verifico por otro canal (llamada o chat oficial) antes de hacer nada",
                    "Respondo al correo pidiendo confirmar", "Reenvío el correo a mis compañeros"],
        "correct_index": 1,
        "feedback": "Verifica siempre por un canal distinto al del mensaje sospechoso.",
    },
    {
        "title": "Mensaje de 'soporte' que pide tu contraseña",
        "topic": "Contraseñas",
        "scenario": "Alguien que dice ser de soporte técnico te escribe por WhatsApp y te pide tu contraseña para 'actualizar tu cuenta'. ¿Qué haces?",
        "options": ["Se la doy, es soporte", "Solo le doy los primeros caracteres",
                    "No la comparto y aviso al área de seguridad", "Cambio mi contraseña y se la envío"],
        "correct_index": 2,
        "feedback": "Nadie legítimo te pedirá tu contraseña. Repórtalo.",
    },
]


def ensure_demo_challenges(db: Session, company: Company, manager: User) -> int:
    """Crea los retos demo que falten. Devuelve cuántos creó."""
    created = 0
    for item in DEMO_CHALLENGES:
        exists = db.scalar(select(Challenge.id).where(Challenge.company_id == company.id, Challenge.title == item["title"]))
        if exists:
            continue
        db.add(Challenge(company_id=company.id, status="published", created_by=manager.id, **item))
        created += 1
    db.commit()
    return created
