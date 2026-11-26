"""Correos de InkaSec: código de verificación (2FA) y bienvenida a gestores y administradores nuevos.

Tres proveedores, elegidos con EMAIL_BACKEND:
- console: imprime el código en la terminal. Solo para desarrollo local (en producción se rechaza).
- smtp: servidor SMTP con STARTTLS (p. ej. Gmail con contraseña de aplicación).
- brevo: API HTTP de Brevo. Render gratuito bloquea el SMTP saliente, así que aquí se usa HTTPS.
"""
from __future__ import annotations
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from app.core.config import settings

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
TIMEOUT_SECONDS = 15
SUBJECT = "Tu código de acceso a InkaSec"
WELCOME_SUBJECT = "Tu cuenta de InkaSec fue creada"


class EmailDeliveryError(Exception):
    """El correo no pudo enviarse. Nunca incluye el código ni la contraseña en el mensaje."""


def _body(code: str) -> str:
    return (
        "Hola,\n\n"
        f"Tu código de acceso a InkaSec es: {code}\n\n"
        "Vence en 5 minutos. Si no intentaste iniciar sesión, ignora este mensaje y cambia tu contraseña.\n\n"
        "Nunca compartas este código con nadie, ni siquiera con personal de soporte."
    )


def _welcome_body(name: str, email: str, role_label: str, temporary_password: str, login_url: str) -> str:
    return (
        f"Hola {name},\n\n"
        f"Un administrador creó tu cuenta de {role_label} en InkaSec.\n\n"
        f"Ingresa en: {login_url}\n"
        f"Correo: {email}\n"
        f"Contraseña inicial: {temporary_password}\n\n"
        "Cada vez que inicies sesión te enviaremos un código de 6 dígitos a este mismo correo "
        "(verificación en dos pasos).\n\n"
        "Si no esperabas este mensaje, ignóralo y avisa a tu administrador. "
        "Nunca compartas tu contraseña ni tus códigos con nadie."
    )


def _deliver(to: str, subject: str, body: str) -> None:
    backend = settings.email_backend
    if backend == "console":
        if settings.is_production:
            raise EmailDeliveryError("El envío por consola está deshabilitado en producción")
        # Solo desarrollo: el contenido (código o contraseña inicial) se imprime en la terminal de la API.
        print(f"[InkaSec · solo desarrollo] {subject} -> {to}\n{body}", flush=True)
    elif backend == "smtp":
        _send_smtp(to, subject, body)
    elif backend == "brevo":
        _send_brevo(to, subject, body)
    else:  # pragma: no cover - el validador de configuración ya lo impide
        raise EmailDeliveryError("Proveedor de correo desconocido")


def send_login_code(to: str, code: str) -> None:
    _deliver(to, SUBJECT, _body(code))


def send_welcome_email(to: str, *, name: str, role_label: str, temporary_password: str) -> None:
    """Avisa a un gestor o administrador recién creado y le entrega su contraseña inicial."""
    login_url = settings.frontend_origin.strip().rstrip("/")
    _deliver(to, WELCOME_SUBJECT, _welcome_body(name, to, role_label, temporary_password, login_url))


def _send_smtp(to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.email_from_name, settings.email_from))
    message["To"] = to
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=TIMEOUT_SECONDS) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError("Fallo SMTP") from exc


def _send_brevo(to: str, subject: str, body: str) -> None:
    payload = {
        "sender": {"name": settings.email_from_name, "email": settings.email_from},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    headers = {"api-key": settings.brevo_api_key, "accept": "application/json"}
    try:
        response = httpx.post(BREVO_URL, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise EmailDeliveryError("Fallo de red con Brevo") from exc
    if response.status_code not in (200, 201, 202):
        raise EmailDeliveryError(f"Brevo respondió {response.status_code}")


def mask_email(email: str) -> str:
    """j***@gmail.com: para mostrar a dónde se envió el código sin exponerlo completo."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if local and domain else "***"
