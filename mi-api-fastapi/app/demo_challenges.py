"""Los retos de demostración (dos rápidos, uno por pasos y uno de señales) para el trabajador. Se usan en el seed demo y en dev_seed_challenges.

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
    {
        "title": "Llamada de 'soporte' que pide acceso remoto",
        "topic": "Ingeniería social",
        "kind": "steps",
        "scenario": "Son las 5:40 p. m. Suena tu anexo: alguien dice ser de soporte técnico y que tu computadora está enviando virus a toda la red.",
        "options": [], "correct_index": 0,
        "content": {"steps": [
            {"prompt": "Te pide instalar un programa de acceso remoto 'para limpiar el virus ahora mismo'. ¿Qué haces?",
             "options": [
                 {"text": "Lo instalo: si es un virus, hay que actuar rápido", "safe": False,
                  "feedback": "La urgencia es el anzuelo. Con acceso remoto, el atacante controla tu equipo y tus sesiones abiertas."},
                 {"text": "Le digo que primero verificaré la llamada con la mesa de ayuda oficial", "safe": True,
                  "feedback": "Bien: verificas por un canal que tú eliges, no por el que te ofrece quien llama."},
                 {"text": "Le pido su nombre y lo instalo si suena convincente", "safe": False,
                  "feedback": "Un nombre y un tono seguro no prueban nada: es lo primero que un estafador prepara."}]},
            {"prompt": "Insiste: te da un 'número de ticket' y dice que tu jefe ya lo autorizó. ¿Qué haces?",
             "options": [
                 {"text": "Si hay ticket y mi jefe autorizó, sigo sus pasos", "safe": False,
                  "feedback": "El ticket y la mención del jefe son parte del guion para darte confianza. No los puedes comprobar en la llamada."},
                 {"text": "Cuelgo con amabilidad y llamo yo al número oficial de soporte", "safe": True,
                  "feedback": "Correcto: cortar la llamada no es descortés; es el paso que rompe el engaño."},
                 {"text": "Le pido que me envíe el programa por correo para instalarlo después", "safe": False,
                  "feedback": "Así recibes el mismo riesgo por otro canal. El problema es el programa, no el momento."}]},
            {"prompt": "Soporte oficial te confirma que nadie te llamó. ¿Qué haces ahora?",
             "options": [
                 {"text": "Nada, no instalé nada", "safe": False,
                  "feedback": "Que no caíste es bueno, pero el atacante probará con tus compañeros. Avisar protege al equipo."},
                 {"text": "Reporto la llamada al área de seguridad con la hora y lo que pidió", "safe": True,
                  "feedback": "Así seguridad puede alertar a otros y bloquear el número. Ese reporte es la acción más valiosa."}]},
        ]},
        "feedback": "Ante una llamada inesperada que pide acceso o datos: verifica por un canal oficial y reporta.",
    },
    {
        "title": "Correo: 'Tu cuenta será suspendida hoy'",
        "topic": "Phishing",
        "kind": "signals",
        "scenario": "Este correo llegó a tu bandeja a las 8:05 a. m. Marca todo lo que te parezca sospechoso y luego revisa.",
        "options": [], "correct_index": 0,
        "content": {"segments": [
            {"field": "from", "text": "Soporte Microsoft 365 <alertas@micros0ft-seguridad.com>", "suspicious": True,
             "explanation": "El dominio imita a Microsoft con un cero en lugar de la letra o. Los avisos reales llegan de dominios oficiales."},
            {"field": "subject", "text": "URGENTE: tu cuenta será suspendida hoy", "suspicious": True,
             "explanation": "La urgencia y la amenaza buscan que actúes sin pensar."},
            {"field": "body", "text": "Hola, colaborador:", "suspicious": True,
             "explanation": "Un saludo genérico: el sistema real sabe tu nombre."},
            {"field": "body", "text": "Detectamos actividad inusual en tu buzón. Si no validas tus datos en las próximas 2 horas, perderás el acceso a tu correo.", "suspicious": True,
             "explanation": "Plazo corto y castigo: presión típica del phishing."},
            {"field": "link", "text": "Validar mi cuenta → http://login-m365.verificar-cuenta.co/acceso", "suspicious": True,
             "explanation": "El enlace no lleva a un sitio oficial de Microsoft. Pasa el cursor sobre los enlaces antes de hacer clic."},
            {"field": "body", "text": "Si tienes dudas, comunícate con la mesa de ayuda de tu empresa.", "suspicious": False,
             "explanation": "Esta frase es normal. Los atacantes mezclan frases legítimas para parecer confiables; no basta con una señal buena."},
            {"field": "attachment", "text": "Formulario_validacion.html", "suspicious": True,
             "explanation": "Un adjunto .html puede abrir una página falsa de inicio de sesión sin pasar por un enlace."},
        ]},
        "feedback": "Ante la duda, no hagas clic: entra al servicio escribiendo tú la dirección y reporta el correo.",
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
