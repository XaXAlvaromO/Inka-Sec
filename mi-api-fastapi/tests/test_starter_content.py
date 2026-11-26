"""El primer gestor de una empresa nueva recibe módulos y retos de ejemplo, ya publicados,
para no empezar de cero (ver app/services/starter_content.py)."""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.main import app
from app.models.models import Area, Company, User
from conftest import API, PASSWORD, csrf, login


def fresh_company(db):
    """Una empresa recién creada, sin ningún módulo ni reto propio todavía."""
    co = Company(name="Nueva SAC", slug="nueva-sac")
    db.add(co); db.commit()
    area = Area(company_id=co.id, name="Operaciones")
    db.add(area); db.commit()
    admin = User(company_id=co.id, area_id=area.id, name="admin-nuevo", email="admin-nuevo@x.pe",
                 password_hash=hash_password(PASSWORD), role="admin")
    db.add(admin); db.commit()
    return SimpleNamespace(co=co, area=area, admin=admin)


def create_manager(admin_client, db, name, email, area):
    """Crea un gestor y devuelve un cliente ya logueado con su contraseña temporal
    (la de `world` no sirve: cada gestor recibe una al azar)."""
    r = admin_client.post(f"{API}/admin/users", json={"name": name, "email": email, "area": area, "role": "manager"},
                          headers=csrf(admin_client))
    assert r.status_code == 200
    row = next(u for u in admin_client.get(f"{API}/admin/users").json() if u["email"] == email)
    user = db.get(User, row["id"])
    client = TestClient(app)
    assert login(client, user, password=r.json()["temporary_password"]).status_code == 200
    return client


def test_first_manager_of_a_new_company_gets_starter_content(db, client_for):
    company = fresh_company(db)
    admin = client_for(company.admin)
    gestor = create_manager(admin, db, "Gestora Nueva", "gestora.nueva@x.pe", "Operaciones")
    content = gestor.get(f"{API}/manager/assignable").json()
    modules = [c for c in content if c["item_type"] == "module"]
    challenges = [c for c in content if c["item_type"] == "challenge"]
    assert len(modules) == 7            # los 7 módulos COM-B de ejemplo
    assert len(challenges) == 4         # los 4 retos de demostración


def test_starter_content_is_not_duplicated_for_a_second_manager(db, client_for):
    company = fresh_company(db)
    admin = client_for(company.admin)
    create_manager(admin, db, "Primera", "primera@x.pe", "Operaciones")
    segunda = create_manager(admin, db, "Segunda", "segunda@x.pe", "Operaciones")
    content = segunda.get(f"{API}/manager/assignable").json()
    # El contenido ya existía (de la primera gestora): no se duplica para la segunda.
    assert len([c for c in content if c["item_type"] == "module"]) == 7
    assert len([c for c in content if c["item_type"] == "challenge"]) == 4


def test_starter_content_is_skipped_for_a_company_with_its_own_content(world, client_for):
    # world.co ya tiene 4 módulos y 2 retos propios, de otro gestor (ver tests/conftest.py).
    admin = client_for(world.adm)
    before = client_for(world.mgr).get(f"{API}/manager/assignable").json()
    r = admin.post(f"{API}/admin/users", json={"name": "Gestora", "email": "gestora.extra@x.pe",
                   "area": "Finanzas", "role": "manager"}, headers=csrf(admin))
    assert r.status_code == 200

    # No hace falta loguear a la nueva gestora: basta con que el contenido de la empresa no haya crecido.
    after = client_for(world.mgr).get(f"{API}/manager/assignable").json()
    assert len(after) == len(before) == 6   # 4 módulos + 2 retos, sin agregados
