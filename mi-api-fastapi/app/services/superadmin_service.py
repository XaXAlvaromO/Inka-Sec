"""Lógica del superadministrador: alta de empresas y su primer administrador, vista de
todas las empresas, y gestión de cualquier usuario sin importar a qué empresa pertenezca.

Reglas que vienen del pedido de Vero:
- El superadministrador empieza una empresa creando su primer administrador; de ahí en
  adelante ese administrador gestiona su propio gestor y usuarios (sin cambios: ya existía).
- El superadministrador ve todas las empresas; un administrador normal solo ve la suya
  (eso ya lo garantiza company_id en app/api/routes/admin.py; aquí no se toca).
- La cuenta de superadministrador nunca se puede eliminar, desactivar ni degradar, ni
  siquiera por otro superadministrador o por sí misma.
"""
import re
import secrets
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.constants import PLATFORM_COMPANY_SLUG
from app.core.security import hash_password
from app.models.models import Company, User
from app.repositories.user_repository import get_by_email, list_by_company, normalize_email
from app.schemas.user import ROLE_LABELS, user_row
from app.services.audit_service import record_audit
from app.services.email_service import EmailDeliveryError, send_welcome_email

SLUG_MAX_LENGTH = 80


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return (base or "empresa")[:SLUG_MAX_LENGTH]


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug, suffix = base, 2
    while db.scalar(select(Company).where(Company.slug == slug)):
        slug = f"{base}-{suffix}"[:SLUG_MAX_LENGTH]
        suffix += 1
    return slug


def list_companies(db: Session) -> list[dict]:
    """Todas las empresas cliente (la empresa interna de la plataforma no se lista: no es
    una empresa que el superadministrador deba "gestionar", es donde vive su propia cuenta)."""
    rows = db.execute(
        select(
            Company.id, Company.name, Company.slug, Company.created_at,
            func.count(User.id),
            func.sum(case((User.role == "admin", 1), else_=0)),
        )
        .outerjoin(User, User.company_id == Company.id)
        .where(Company.slug != PLATFORM_COMPANY_SLUG)
        .group_by(Company.id, Company.name, Company.slug, Company.created_at)
        .order_by(Company.name)
    ).all()
    return [
        {"id": cid, "name": name, "slug": slug, "created_at": created.isoformat(), "users": total or 0, "admins": admins or 0}
        for cid, name, slug, created, total, admins in rows
    ]


def create_company(db: Session, *, actor: User, company_name: str, admin_name: str, admin_email: str, ip: str | None) -> dict:
    email = normalize_email(admin_email)
    if get_by_email(db, email):
        raise HTTPException(409, "El correo ya existe")
    if db.scalar(select(Company).where(func.lower(Company.name) == company_name.strip().lower())):
        raise HTTPException(409, "Ya existe una empresa con ese nombre")
    company = Company(name=company_name.strip(), slug=_unique_slug(db, company_name))
    db.add(company)
    db.commit()
    db.refresh(company)
    # Sin área todavía: el propio administrador crea sus áreas al entrar (como ya podía hacer).
    temporary_password = secrets.token_urlsafe(15)
    admin = User(company_id=company.id, area_id=None, name=admin_name.strip(), email=email, password_hash=hash_password(temporary_password), role="admin", is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    try:
        send_welcome_email(email, name=admin.name, role_label=ROLE_LABELS["admin"], temporary_password=temporary_password)
        email_sent = True
    except EmailDeliveryError:
        email_sent = False
    record_audit(db, action="COMPANY_CREATED", result="success", user=actor, ip=ip, company_id=company.id,
                 details={"company_id": company.id, "company_name": company.name, "admin_user_id": admin.id, "welcome_email_sent": email_sent})
    return {"company": {"id": company.id, "name": company.name, "slug": company.slug}, **user_row(admin), "temporary_password": temporary_password, "email_sent": bool(email_sent)}


def _client_company_or_404(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if not company or company.slug == PLATFORM_COMPANY_SLUG:
        raise HTTPException(404, "Empresa no encontrada")
    return company


def list_company_users(db: Session, company_id: int) -> list[dict]:
    _client_company_or_404(db, company_id)
    return [user_row(u) for u in list_by_company(db, company_id)]


def _any_user_or_404(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


def _ensure_not_superadmin(u: User):
    # Protege a cualquier cuenta de superadministrador, no solo a la del que llama: así
    # ni siquiera otro superadministrador futuro podría eliminar o degradar a este.
    if u.role == "superadmin":
        raise HTTPException(403, "La cuenta de superadministrador no se puede modificar ni eliminar")


def update_any_user(db: Session, *, actor: User, user_id: int, payload, ip: str | None) -> dict:
    u = _any_user_or_404(db, user_id)
    _ensure_not_superadmin(u)
    if u.id == actor.id:
        raise HTTPException(400, "No puedes cambiar tu propio rol ni desactivar tu cuenta")
    old_role = u.role
    if payload.role is not None:
        u.role = payload.role
    if payload.is_active is not None:
        u.is_active = payload.is_active
    db.commit()
    record_audit(db, action="ROLE_CHANGED" if old_role != u.role else "USER_UPDATED", result="success", user=actor, ip=ip, company_id=u.company_id,
                 details={"target_user_id": u.id, "old_role": old_role, "new_role": u.role, "by_superadmin": True})
    return {"ok": True}


def delete_any_user(db: Session, *, actor: User, user_id: int, ip: str | None) -> dict:
    u = _any_user_or_404(db, user_id)
    _ensure_not_superadmin(u)
    if u.id == actor.id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    target_company_id, target_user_id = u.company_id, u.id
    db.delete(u)
    db.commit()
    record_audit(db, action="USER_DELETED", result="success", user=actor, ip=ip, company_id=target_company_id,
                 details={"target_user_id": target_user_id, "by_superadmin": True})
    return {"ok": True}
