"""Superadministrador: alta de empresas con su primer administrador, vista de todas las
empresas, gestión de cualquier usuario y protección de la propia cuenta de superadministrador.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.models import Company, User
from conftest import API, WELCOME_OUTBOX, csrf, login


def test_superadmin_requires_2fa_to_login(world, client_for):
    client = client_for()
    r = login(client, world.super)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "superadmin"


def test_superadmin_lists_only_client_companies_not_the_platform_company(world, client_for):
    sup = client_for(world.super)
    r = sup.get(f"{API}/superadmin/companies")
    assert r.status_code == 200
    names = {c["name"] for c in r.json()}
    assert {"A", "B"} <= names
    assert world.platform.name not in names


def test_superadmin_company_listing_counts_users_and_admins(world, client_for):
    sup = client_for(world.super)
    rows = {c["id"]: c for c in sup.get(f"{API}/superadmin/companies").json()}
    row = rows[world.co.id]
    # world.co tiene w1, w2 (worker), mgr (manager) y adm (admin): 4 usuarios, 1 administrador.
    assert row["users"] == 4 and row["admins"] == 1


def test_superadmin_creates_company_with_admin_and_sends_welcome_email(world, client_for, db):
    sup = client_for(world.super)
    payload = {"company_name": "Nueva Empresa SAC", "admin_name": "Rosa Admin", "admin_email": "rosa@nueva.pe"}
    r = sup.post(f"{API}/superadmin/companies", json=payload, headers=csrf(sup))
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "Administrador" and body["email_sent"] is True and body["temporary_password"]
    assert body["company"]["name"] == "Nueva Empresa SAC"

    db.expire_all()
    company = db.scalar(select(Company).where(Company.name == "Nueva Empresa SAC"))
    assert company is not None and company.slug == "nueva-empresa-sac"
    admin = db.scalar(select(User).where(User.email == "rosa@nueva.pe"))
    assert admin.role == "admin" and admin.company_id == company.id and admin.area_id is None

    sent = WELCOME_OUTBOX[-1]
    assert sent["to"] == "rosa@nueva.pe" and sent["role_label"] == "Administrador"
    assert sent["temporary_password"] == body["temporary_password"]

    # El administrador recién creado inicia sesión con la contraseña temporal (no con la
    # PASSWORD genérica de la fixture) y solo ve su propia empresa, vacía de todo lo demás.
    new_admin_client = TestClient(app)
    assert login(new_admin_client, admin, password=body["temporary_password"]).status_code == 200
    assert new_admin_client.get(f"{API}/admin/users").json() == [
        {"id": admin.id, "name": "Rosa Admin", "email": "rosa@nueva.pe", "area": "Sin área", "role": "Administrador", "status": "Activo", "twoFactor": True}
    ]


def test_superadmin_cannot_create_company_with_duplicate_name(world, client_for):
    sup = client_for(world.super)
    first = {"company_name": "Constructora Lima", "admin_name": "Primer Admin", "admin_email": "primero@lima.pe"}
    assert sup.post(f"{API}/superadmin/companies", json=first, headers=csrf(sup)).status_code == 201
    # Sin distinguir mayúsculas/minúsculas: "constructora lima" también cuenta como duplicado.
    second = {"company_name": "constructora lima", "admin_name": "Otro Admin", "admin_email": "otro@lima.pe"}
    assert sup.post(f"{API}/superadmin/companies", json=second, headers=csrf(sup)).status_code == 409


def test_superadmin_cannot_create_admin_with_duplicate_email(world, client_for):
    sup = client_for(world.super)
    payload = {"company_name": "Empresa C", "admin_name": "Duplicado", "admin_email": world.adm.email}
    assert sup.post(f"{API}/superadmin/companies", json=payload, headers=csrf(sup)).status_code == 409


def test_superadmin_lists_users_of_any_company(world, client_for):
    sup = client_for(world.super)
    emails_a = {u["email"] for u in sup.get(f"{API}/superadmin/companies/{world.co.id}/users").json()}
    emails_b = {u["email"] for u in sup.get(f"{API}/superadmin/companies/{world.other.id}/users").json()}
    assert world.adm.email in emails_a and world.mgr.email in emails_a
    assert world.outsider.email in emails_b and world.outsider.email not in emails_a


def test_superadmin_company_users_404_for_unknown_or_platform_company(world, client_for):
    sup = client_for(world.super)
    assert sup.get(f"{API}/superadmin/companies/999999/users").status_code == 404
    # La empresa interna de la plataforma no se gestiona como una empresa cliente.
    assert sup.get(f"{API}/superadmin/companies/{world.platform.id}/users").status_code == 404


def test_superadmin_can_deactivate_and_delete_users_of_any_company(world, client_for, db):
    sup = client_for(world.super)
    url = f"{API}/superadmin/users/{world.outsider.id}"
    assert sup.patch(url, json={"is_active": False}, headers=csrf(sup)).status_code == 200
    db.expire_all()
    assert db.get(User, world.outsider.id).is_active is False

    assert sup.delete(f"{API}/superadmin/users/{world.w1.id}", headers=csrf(sup)).status_code == 200
    # select() en vez de db.get(): el objeto ya vivía en la sesión de la prueba (lo creó la
    # fixture world) y otra sesión lo borró; get() intentaría refrescarlo y lanzaría
    # ObjectDeletedError en vez de devolver None.
    assert db.scalar(select(User).where(User.id == world.w1.id)) is None


def test_superadmin_account_can_never_be_demoted_deactivated_or_deleted(world, client_for, db):
    sup = client_for(world.super)
    url = f"{API}/superadmin/users/{world.super.id}"
    assert sup.patch(url, json={"is_active": False}, headers=csrf(sup)).status_code == 403
    assert sup.patch(url, json={"role": "admin"}, headers=csrf(sup)).status_code == 403
    assert sup.delete(url, headers=csrf(sup)).status_code == 403
    db.expire_all()
    me = db.get(User, world.super.id)
    assert me.role == "superadmin" and me.is_active is True
