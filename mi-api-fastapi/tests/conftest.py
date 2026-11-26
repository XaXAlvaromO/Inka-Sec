"""Configuración compartida de las pruebas.

Las variables se fijan ANTES de importar la app: así las pruebas nunca usan la base
de datos real ni dependen del .env local, y el resultado es igual en CI y en tu PC.
"""
import os

os.environ.update({
    "APP_ENV": "test",
    "API_PREFIX": "/api/v1",
    "DATABASE_URL": "sqlite://",
    "JWT_SECRET_KEY": "clave-solo-para-pruebas-no-usar-en-produccion-0123456789",
    "SEED_DEMO_DATA": "false",
    "AUTO_CREATE_TABLES": "false",
    "COOKIE_SECURE": "false",
    "COOKIE_SAMESITE": "lax",
    "TRUSTED_PROXY_HOPS": "0",
    "EMAIL_BACKEND": "console",  # el .env local puede tener SMTP real: las pruebas nunca deben enviar correos
    "FRONTEND_ORIGIN": "http://localhost:5173",
})

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.middleware import auth_rate_limiter
from app.core.security import hash_password
from app.db.session import Base, get_db
from app.services import auth_service
from app.api.routes import admin as admin_routes
from app.services import superadmin_service
from app.core.constants import PLATFORM_COMPANY_NAME, PLATFORM_COMPANY_SLUG
from app.models.challenge import Challenge
from app.models.models import Area, Company, LearningModule, User

API = "/api/v1"
PASSWORD = "Clave-Segura-2026"

# Correos 2FA "enviados" durante la prueba: (destinatario, código). Nunca sale nada a internet.
OUTBOX: list[tuple[str, str]] = []
# Correos de bienvenida (gestores/administradores nuevos): dicts con to, name, role_label, temporary_password.
WELCOME_OUTBOX: list[dict] = []


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    auth_rate_limiter.reset()
    yield
    auth_rate_limiter.reset()


@pytest.fixture(autouse=True)
def _capture_login_codes(monkeypatch):
    OUTBOX.clear()
    WELCOME_OUTBOX.clear()
    monkeypatch.setattr(auth_service, "send_login_code", lambda to, code: OUTBOX.append((to, code)))
    monkeypatch.setattr(admin_routes, "send_welcome_email", lambda to, **kw: WELCOME_OUTBOX.append({"to": to, **kw}))
    monkeypatch.setattr(superadmin_service, "send_welcome_email", lambda to, **kw: WELCOME_OUTBOX.append({"to": to, **kw}))
    yield
    OUTBOX.clear()
    WELCOME_OUTBOX.clear()


def code_for(user) -> str:
    """Último código 2FA enviado al correo de este usuario."""
    return next(code for to, code in reversed(OUTBOX) if to == user.email)


@pytest.fixture
def Session():
    """Base SQLite en memoria, nueva en cada prueba."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def db(Session):
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(PASSWORD)  # Argon2 es lento a propósito: se calcula una sola vez


@pytest.fixture
def world(db, password_hash):
    """Dos empresas: A (la nuestra) y B (ajena), con usuarios, módulos y retos."""
    co, other = Company(name="A", slug="a"), Company(name="B", slug="b")
    db.add_all([co, other]); db.commit()
    area, other_area = Area(company_id=co.id, name="Finanzas"), Area(company_id=other.id, name="Ventas")
    db.add_all([area, other_area]); db.commit()

    def user(name, role, company=co, user_area=area):
        u = User(company_id=company.id, area_id=user_area.id, name=name, email=f"{name}@x.pe",
                 password_hash=password_hash, role=role)
        db.add(u); db.commit(); return u

    def module(slug, status="published", company=co, by=None):
        m = LearningModule(company_id=company.id, slug=slug, title=slug, topic="Credenciales",
                           behavior_objective="x", status=status, content_json={"title": slug}, created_by=by)
        db.add(m); db.commit(); return m

    def challenge(title, company=co, by=None):
        c = Challenge(company_id=company.id, title=title, topic="Phishing", scenario="s", options=["a", "b", "c"],
                      correct_index=1, feedback="fb", status="published", created_by=by)
        db.add(c); db.commit(); return c

    # Empresa interna de la plataforma (no es una empresa cliente): aquí vive el superadministrador,
    # igual que en una instalación real (app/bootstrap_admin.py crea la misma separación).
    platform = Company(name=PLATFORM_COMPANY_NAME, slug=PLATFORM_COMPANY_SLUG)
    db.add(platform); db.commit()

    w = SimpleNamespace(co=co, other=other, platform=platform, area=area)
    w.w1, w.w2 = user("ana", "worker"), user("luis", "worker")
    w.mgr, w.adm = user("gestor", "manager"), user("admin", "admin")
    w.outsider = user("otro", "worker", company=other, user_area=other_area)
    w.super = User(company_id=platform.id, area_id=None, name="superadmin", email="superadmin@x.pe", password_hash=password_hash, role="superadmin")
    db.add(w.super); db.commit()
    w.mods = [module(f"m{i}", by=w.mgr.id) for i in range(4)]
    w.draft = module("borrador", status="draft", by=w.mgr.id)
    w.foreign = module("ajeno", company=other)
    w.c1, w.c2 = challenge("r1", by=w.mgr.id), challenge("r2", by=w.mgr.id)
    w.foreign_challenge = challenge("ajeno", company=other)
    return w


def csrf(client) -> dict:
    """Cabecera que el frontend envía en cada POST/PATCH/DELETE (double submit cookie)."""
    return {"x-csrf-token": client.cookies.get("inka_csrf") or ""}


def wrong_code(code: str) -> str:
    """Un código de 6 dígitos distinto al dado (el siguiente módulo 10^6)."""
    return f"{(int(code) + 1) % 1_000_000:06d}"


def start_login(client, user, password=PASSWORD):
    return client.post(f"{API}/auth/login", json={"email": user.email, "password": password})


def login(client, user, password=PASSWORD):
    """Inicio de sesión completo, con 2FA real para gestor y administrador."""
    r = start_login(client, user, password)
    if r.status_code == 200 and r.json().get("requires_2fa"):
        r = client.post(f"{API}/auth/2fa/verify", json={"challenge_id": r.json()["challenge_id"], "code": code_for(user)})
    return r


@pytest.fixture
def client_for(Session):
    """client_for(usuario) devuelve un navegador simulado con la sesión ya iniciada."""
    def make(user=None):
        client = TestClient(app)
        if user is not None:
            r = login(client, user)
            assert r.status_code == 200, r.text
        return client
    return make
