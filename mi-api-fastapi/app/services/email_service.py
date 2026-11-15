"""Envío de códigos de verificación por correo (segundo factor de gestores y administradores).

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


class EmailDeliveryError(Exception):
    """El código no pudo enviarse. Nunca incluye el código ni la contraseña en el mensaje."""


def _body(code: str) -> str:
    return (
        "Hola,\n\n"
        f"Tu código de acceso a InkaSec es: {code}\n\n"
        "Vence en 5 minutos. Si no intentaste iniciar sesión, ignora este mensaje y cambia tu contraseña.\n\n"
        "Nunca compartas este código con nadie, ni siquiera con personal de soporte."
    )


def send_login_code(to: str, code: str) -> None:
    backend = settings.email_backend
    if backend == "console":
        if settings.is_production:
            raise EmailDeliveryError("El envío por consola está deshabilitado en producción")
        print(f"[InkaSec · solo desarrollo] Código 2FA para {to}: {code}", flush=True)
    elif backend == "smtp":
        _send_smtp(to, code)
    elif backend == "brevo":
        _send_brevo(to, code)
    else:  # pragma: no cover - el validador de configuración ya lo impide
        raise EmailDeliveryError("Proveedor de correo desconocido")


def _send_smtp(to: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = formataddr((settings.email_from_name, settings.email_from))
    message["To"] = to
    message.set_content(_body(code))
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=TIMEOUT_SECONDS) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError("Fallo SMTP") from exc


def _send_brevo(to: str, code: str) -> None:
    payload = {
        "sender": {"name": settings.email_from_name, "email": settings.email_from},
        "to": [{"email": to}],
        "subject": SUBJECT,
        "textContent": _body(code),
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
