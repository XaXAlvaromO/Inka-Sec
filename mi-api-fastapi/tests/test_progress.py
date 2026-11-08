"""Reglas de progreso, vistas a través de las rutas que realmente usa el frontend."""
from conftest import API, csrf


def complete(client, module):
    return client.post(f"{API}/worker/modules/{module.id}/complete", headers=csrf(client))


def answer(client, challenge, choice):
    return client.post(f"{API}/worker/challenges/{challenge.id}/answer", json={"choice": choice}, headers=csrf(client))


def test_module_percentage_counts_only_confirmed_modules(world, client_for):
    worker = client_for(world.w1)
    r = complete(worker, world.mods[0])
    assert r.status_code == 200
    assert r.json()["modules"] == {"completed": 1, "total": 4, "percent": 25}   # el borrador no cuenta
    assert complete(worker, world.mods[0]).json()["modules"]["completed"] == 1   # idempotente
    dash = worker.get(f"{API}/worker/dashboard").json()
    assert dash["progress"] == 25 and dash["stats"][0]["value"] == "1 / 4"
    assert {m["id"]: m["progress"] for m in dash["modules"]}[world.mods[0].id] == 100


def test_cannot_complete_draft_or_foreign_module(world, client_for):
    worker = client_for(world.w1)
    for module in (world.draft, world.foreign):
        assert complete(worker, module).status_code == 404


def test_challenge_single_attempt_and_validation(world, client_for):
    worker = client_for(world.w1)
    assert answer(worker, world.c1, 9).status_code == 422             # opción fuera de rango
    r = answer(worker, world.c1, 0)
    assert r.status_code == 200 and r.json()["is_correct"] is False and r.json()["correct_index"] == 1
    assert answer(worker, world.c1, 1).status_code == 409             # un solo intento
    dash = worker.get(f"{API}/worker/dashboard").json()
    assert dash["challenge"]["id"] == world.c2.id
    assert dash["stats"][1]["value"] == "0 / 2" and dash["stats"][1]["helper"] == "1 respondidos"
    assert dash["weakTopics"] == [{"topic": "Phishing", "errors": 1}]


def test_dashboard_has_no_challenge_when_all_are_answered(world, client_for):
    worker = client_for(world.w1)
    answer(worker, world.c1, 1); answer(worker, world.c2, 1)
    assert worker.get(f"{API}/worker/dashboard").json()["challenge"] is None   # el front muestra un estado vacío


def test_manager_dashboard_is_scoped_to_own_content(world, client_for):
    worker = client_for(world.w1)
    complete(worker, world.mods[0])
    answer(worker, world.c1, 1); answer(worker, world.c2, 0)
    dash = client_for(world.mgr).get(f"{API}/manager/dashboard").json()
    success = {row["id"]: row["success"] for row in dash["content"]}
    assert success[world.mods[0].id] == 50                              # 1 de 2 trabajadores activos
    assert dash["stats"][2]["value"] == "50%"                           # 1 acierto en 2 intentos
    assert dash["topicErrors"][0]["topic"] == "Phishing" and dash["topicErrors"][0]["errors"] == 1


def test_manager_creates_draft_content(world, client_for):
    manager = client_for(world.mgr)
    r = manager.post(f"{API}/manager/content", json={"title": "  Wi-Fi público  ", "topic": "Redes", "description": "d"}, headers=csrf(manager))
    assert r.status_code == 200 and r.json()["status"] == "Borrador" and r.json()["title"] == "Wi-Fi público"


def test_admin_dashboard_and_reports(world, client_for):
    worker = client_for(world.w1)
    complete(worker, world.mods[0]); complete(worker, world.mods[1])
    admin = client_for(world.adm)
    dash = admin.get(f"{API}/admin/dashboard").json()
    assert dash["stats"][1]["value"] == "25%"                            # 2 de 8 posibles
    assert {u["id"]: u["progress"] for u in dash["users"]}[world.w1.id] == 50
    summary = admin.get(f"{API}/admin/reports/summary").json()
    assert summary["total_users"] == 4 and summary["completed_modules"] == 2
    r = admin.get(f"{API}/admin/reports/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert r.text.splitlines()[0] == "area,usuarios,usuarios_activos,avance_promedio_registrado,modulos_completados"


def test_admin_user_lifecycle(world, client_for):
    admin = client_for(world.adm)
    r = admin.post(f"{API}/admin/users", json={"name": "Nueva", "email": "Nueva@X.pe", "area": "Finanzas", "role": "worker"}, headers=csrf(admin))
    assert r.status_code == 200
    created = r.json()
    assert created["email"] == "nueva@x.pe" and created["totp_setup_secret"] is None
    new_user = client_for()
    assert new_user.post(f"{API}/auth/login", json={"email": "nueva@x.pe", "password": created["temporary_password"]}).status_code == 200
    assert admin.post(f"{API}/admin/users", json={"name": "Otra", "email": "nueva@x.pe", "area": "Finanzas"}, headers=csrf(admin)).status_code == 409
    assert admin.patch(f"{API}/admin/users/{created['id']}", json={"is_active": False}, headers=csrf(admin)).status_code == 200
    assert new_user.get(f"{API}/auth/me").status_code == 401              # la sesión muere al desactivar
    assert admin.delete(f"{API}/admin/users/{created['id']}", headers=csrf(admin)).status_code == 200
    audit = admin.get(f"{API}/admin/audit", params={"q": "Usuario creado"}).json()
    assert audit["total"] == 1 and audit["items"][0]["action"] == "USER_CREATED"


def test_admin_areas(world, client_for):
    admin = client_for(world.adm)
    assert admin.post(f"{API}/admin/areas", json={"name": "Legal"}, headers=csrf(admin)).status_code == 201
    assert admin.post(f"{API}/admin/areas", json={"name": "  legal "}, headers=csrf(admin)).status_code == 409
    names = [a["name"] for a in admin.get(f"{API}/admin/areas").json()]
    assert names == ["Finanzas", "Legal"]                                 # no aparecen áreas de otra empresa


def test_worker_saves_comb_diagnostic(world, client_for):
    worker = client_for(world.w1)
    payload = {"phase": "pre", "responses": [{"dimension": "capacidad", "code": "C1", "value": 4}]}
    r = worker.post(f"{API}/worker/modules/{world.mods[0].id}/comb", json=payload, headers=csrf(worker))
    assert r.status_code == 200 and r.json() == {"saved": 1}
    assert worker.get(f"{API}/worker/modules/{world.mods[0].id}").json() == {"title": "m0"}
