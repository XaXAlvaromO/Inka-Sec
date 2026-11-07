import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password, new_totp_secret, totp_code
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Area, AuditLog, Company, LearningModule, ModuleProgress, User


@pytest.fixture
def admin_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    secret = new_totp_secret()
    with session_factory() as db:
        company = Company(name="Empresa A", slug="empresa-a")
        other_company = Company(name="Empresa B", slug="empresa-b")
        db.add_all([company, other_company])
        db.flush()
        area = Area(company_id=company.id, name="Tecnología")
        other_area = Area(company_id=other_company.id, name="Privada")
        db.add_all([area, other_area])
        db.flush()
        admin = User(company_id=company.id, area_id=area.id, name="Admin A", email="admin-a@example.com", password_hash=hash_password("test-password"), role="admin", totp_secret=secret, is_active=True)
        worker = User(company_id=company.id, area_id=area.id, name="Trabajador A", email="worker-a@example.com", password_hash=hash_password("test-password"), role="worker", is_active=True)
        outsider = User(company_id=other_company.id, area_id=other_area.id, name="Usuario B", email="worker-b@example.com", password_hash=hash_password("test-password"), role="worker", is_active=True)
        db.add_all([admin, worker, outsider])
        db.flush()
        module = LearningModule(company_id=company.id, slug="modulo", title="Módulo", topic="Tema", behavior_objective="Objetivo", status="published", content_json={})
        db.add(module)
        db.flush()
        db.add(ModuleProgress(user_id=worker.id, module_id=module.id, progress=100))
        db.add(AuditLog(company_id=other_company.id, user_id=outsider.id, action="PRIVATE_EVENT", result="success", ip_address="10.0.0.2"))
        db.commit()

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/admin/areas").status_code == 401
            login = client.post("/api/v1/auth/login", json={"email": "admin-a@example.com", "password": "test-password"})
            assert login.status_code == 200
            verify = client.post("/api/v1/auth/2fa/verify", json={"challenge_id": login.json()["challenge_id"], "code": totp_code(secret)})
            assert verify.status_code == 200
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_area_creation_and_tenant_scoping(admin_client):
    csrf = {"X-CSRF-Token": admin_client.cookies["inka_csrf"]}
    created = admin_client.post("/api/v1/admin/areas", json={"name": " Finanzas "}, headers=csrf)
    assert created.status_code == 201
    assert created.json()["name"] == "Finanzas"
    duplicate = admin_client.post("/api/v1/admin/areas", json={"name": "finanzas"}, headers=csrf)
    assert duplicate.status_code == 409
    areas = admin_client.get("/api/v1/admin/areas").json()
    assert {area["name"] for area in areas} == {"Finanzas", "Tecnología"}
    users = admin_client.get("/api/v1/admin/users").json()
    assert {user["email"] for user in users} == {"admin-a@example.com", "worker-a@example.com"}
    assert all("area" in user and "status" in user for user in users)


def test_audit_pagination_and_report(admin_client):
    csrf = {"X-CSRF-Token": admin_client.cookies["inka_csrf"]}
    admin_client.post("/api/v1/admin/areas", json={"name": "Ventas"}, headers=csrf)
    first = admin_client.get("/api/v1/admin/audit?limit=1&offset=0").json()
    assert first["total"] >= 2
    assert len(first["items"]) == 1
    assert first["items"][0]["actor"] == "Admin A"
    assert first["items"][0]["ip"]
    second = admin_client.get("/api/v1/admin/audit?limit=1&offset=1").json()
    assert second["items"][0]["id"] != first["items"][0]["id"]
    assert admin_client.get("/api/v1/admin/audit?q=PRIVATE_EVENT").json()["total"] == 0
    assert admin_client.get("/api/v1/admin/audit?q=%C3%A1rea%20creada").json()["total"] == 1

    report = admin_client.get("/api/v1/admin/reports/summary").json()
    assert report["total_users"] == 2
    assert report["average_progress"] == 100
    assert report["completed_modules"] == 1
    assert {area["name"] for area in report["areas"]} == {"Tecnología", "Ventas"}
    exported = admin_client.get("/api/v1/admin/reports/export")
    assert exported.status_code == 200
    assert "avance_promedio_registrado" in exported.text
    assert "Privada" not in exported.text


def test_worker_cannot_access_admin_sections(admin_client):
    login = admin_client.post("/api/v1/auth/login", json={"email": "worker-a@example.com", "password": "test-password"})
    assert login.status_code == 200
    for path in ("users", "areas", "audit", "reports/summary"):
        assert admin_client.get(f"/api/v1/admin/{path}").status_code == 403
