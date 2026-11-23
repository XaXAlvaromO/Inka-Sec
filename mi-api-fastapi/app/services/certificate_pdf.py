"""PDF del certificado, en blanco y negro (se imprime bien en cualquier impresora).

Sin puntaje ni número de intentos: el certificado dice que la persona aprobó, no cuánto sacó.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fpdf import FPDF

from app.core.config import settings
from app.services import visibility

PERU = timezone(timedelta(hours=-5))  # Perú no usa horario de verano


def _text(value: str) -> str:
    """Las fuentes base del PDF usan latin-1: los acentos del español entran; lo demás se reemplaza."""
    replacements = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.encode("latin-1", "replace").decode("latin-1")


def _date(value: datetime) -> str:
    return visibility.aware(value).astimezone(PERU).strftime("%d/%m/%Y")


def verify_url(code: str) -> str:
    return f"{settings.frontend_origin.rstrip('/')}/verificar/{code}"


def render_certificate(cert, *, holder: str, company: str, status: str) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.set_title(_text(f"Certificado InkaSec - {cert.topic}"))
    pdf.set_author("InkaSec")
    pdf.add_page()
    width, height = pdf.w, pdf.h
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)

    # Marco doble
    pdf.set_line_width(1.2)
    pdf.rect(10, 10, width - 20, height - 20)
    pdf.set_line_width(0.3)
    pdf.rect(14, 14, width - 28, height - 28)

    def line(text: str, size: float, style: str = "", gap: float = 0, spacing: float = 0):
        pdf.set_font("Helvetica", style, size)
        pdf.set_char_spacing(spacing)
        pdf.cell(0, size * 0.5, _text(text), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_char_spacing(0)
        if gap:
            pdf.ln(gap)

    pdf.set_y(26)
    line("INKASEC  ·  CAPACITACIÓN EN SEGURIDAD DIGITAL", 9, "B", 6, spacing=1.5)
    line("CERTIFICADO", 30, "B", 2, spacing=4)
    line("de aprobación por tema", 12, "", 10)
    line("Se certifica que", 12, "", 4)
    line(holder, 24, "B", 1)
    pdf.set_line_width(0.3)
    pdf.line(width / 2 - 70, pdf.get_y() + 1, width / 2 + 70, pdf.get_y() + 1)
    pdf.ln(6)
    line(f"de {company}" if company else "", 11, "", 4)
    line("aprobó la ruta de capacitación del tema", 12, "", 3)
    line(cert.topic.upper(), 20, "B", 6, spacing=1)

    modules = list(cert.module_titles or [])
    if modules:
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_x(40)
        pdf.multi_cell(width - 80, 5, _text("Módulos: " + "; ".join(modules) + "."), align="C",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_x(40)
    pdf.multi_cell(width - 80, 4.5, _text(
        "Requisito: completar todos los módulos del tema, con al menos 80 % en las preguntas de práctica, "
        "y registrar la acción real que aplicará en su trabajo. Metodología COM-B (capacidad, oportunidad y motivación)."),
        align="C", new_x="LMARGIN", new_y="NEXT")

    # Pie: fechas a la izquierda, verificación a la derecha
    base = height - 46
    pdf.set_line_width(0.2)
    pdf.line(24, base - 3, width - 24, base - 3)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_xy(24, base)
    pdf.cell(110, 5, _text(f"Emitido el {_date(cert.issued_at)}" + ("  (renovación)" if cert.renewed else "")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(24)
    pdf.cell(110, 5, _text(f"Válido hasta el {_date(cert.expires_at)}"), new_x="LMARGIN", new_y="NEXT")
    if status not in {"active", "expiring"}:
        pdf.set_x(24)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(110, 5, _text("Estado al descargar: " + ("VENCIDO" if status == "expired" else "REEMPLAZADO POR UNA RENOVACIÓN")))

    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(width - 24 - 130, base)
    pdf.cell(130, 5, _text("Código de verificación"), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "B", 12)
    pdf.set_x(width - 24 - 130)
    pdf.cell(130, 6, cert.code, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_x(width - 24 - 130)
    pdf.cell(130, 5, _text(f"Compruébalo en {verify_url(cert.code)}"), align="R")

    return bytes(pdf.output())
