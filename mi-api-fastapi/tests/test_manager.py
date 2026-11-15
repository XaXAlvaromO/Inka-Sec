"""Panel de Contenido del gestor (HU-07 a HU-10): creación, asignación, visibilidad y estadísticas."""
from datetime import datetime, timedelta, timezone

from app.models.models import Area, User
from conftest import API, csrf


def module_payload(**changes):
    body = {
        "title": "Wi-Fi público seguro",
        "topic": "Redes Wi-Fi públicas",
        "objective": "Evitar redes abiertas cuando se maneja información de la empresa.",
        "micro_lesson": "Una red pública puede dejar ver tráfico no cifrado. Usa datos móviles o la VPN corporativa.",
        "capacity_questions": [{"prompt": "¿Qué usas en un café para revisar datos de la empresa?",
                                "options": ["Wi-Fi abierto", "Datos móviles o VPN"], "correct": 1,
                                "feedback": "La VPN cifra tu conexión."}],
        "real_action": "Activa la VPN corporativa antes de abrir el correo en una red pública.",
        "status": "draft",
    }
    body.update(changes)
    return body


def challenge_payload(**changes):
    body = {
        "title": "Pedido de clave por chat",
        "topic": "Phishing",
        "scenario": "Alguien te escribe por chat pidiendo tu clave para desbloquear tu cuenta. ¿Qué haces?",
        "options": ["Se la doy", "La rechazo y aviso a seguridad", "La cambio y se la envío"],
        "correct_index": 1,
        "feedback": "Nadie legítimo pide tu clave.",
        "status": "published",
    }
    body.update(changes)
    return body


def in_days(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def add_user(world, db, password_hash, name, role, area):
    user = User(company_id=world.co.id, area_id=area.id, name=name, email=f"{name}@x.pe",
                password_hash=password_hash, role=role)
    db.add(user); db.commit()
    return user


def add_area(world, db, name):
    area = Area(company_id=world.co.id, name=name)
    db.add(area); db.commit()
    return area


def create_module(manager, **changes):
    return manager.post(f"{API}/manager/modules", json=module_payload(**changes), headers=csrf(manager))


# ---------------------------------------------------------------- HU-07 crear y editar

def test_topics_come_from_the_catalog(world, client_for):
    topics = client_for(world.mgr).get(f"{API}/manager/topics").json()["topics"]
    assert "Contraseñas" in topics and "Redes Wi-Fi públicas" in topics and "Verificación en dos pasos" in topics


def test_manager_creates_draft_module_that_workers_cannot_open(world, client_for):
    manager = client_for(world.mgr)
    r = create_module(manager)
    assert r.status_code == 200 and r.json()["status"] == "draft"
    module_id = r.json()["id"]
    assert client_for(world.w1).get(f"{API}/worker/modules/{module_id}").status_code == 404   # borrador oculto

    body = module_payload(status="published")
    assert manager.put(f"{API}/manager/modules/{module_id}", json=body, headers=csrf(manager)).status_code == 200
    worker = client_for(world.w1).get(f"{API}/worker/modules/{module_id}")
    assert worker.status_code == 200
    assert worker.json()["capacity_questions"][0].get("correct") is None                   # la respuesta no se envía


def test_module_form_round_trips_the_saved_content(world, client_for):
    manager = client_for(world.mgr)
    module_id = create_module(manager, status="published").json()["id"]
    form = manager.get(f"{API}/manager/modules/{module_id}").json()
    assert form["title"] == "Wi-Fi público seguro" and form["capacity_questions"][0]["correct"] == 1
    assert form["real_action"].startswith("Activa la VPN")


def test_module_validation_rejects_bad_input(world, client_for):
    manager = client_for(world.mgr)
    bad = [
        module_payload(topic="Tema inventado"),
        module_payload(capacity_questions=[{"prompt": "¿Qué opción es buena?", "options": ["a", "b"], "correct": 2}]),
        module_payload(capacity_questions=[{"prompt": "¿Qué opción es buena?", "options": ["a"], "correct": 0}]),
        module_payload(capacity_questions=[]),
    ]
    for body in bad:
        assert manager.post(f"{API}/manager/modules", json=body, headers=csrf(manager)).status_code == 422, body


def test_editing_keeps_a_legacy_topic_but_not_an_unknown_one(world, client_for):
    manager = client_for(world.mgr)                        # los módulos base usan el tema heredado "Credenciales"
    mod = world.mods[0]
    keep = manager.put(f"{API}/manager/modules/{mod.id}", json=module_payload(topic="Credenciales", status="published"), headers=csrf(manager))
    assert keep.status_code == 200
    unknown = manager.put(f"{API}/manager/modules/{mod.id}", json=module_payload(topic="Otro", status="published"), headers=csrf(manager))
    assert unknown.status_code == 422


def test_manager_cannot_edit_another_managers_or_foreign_content(world, client_for, db, password_hash):
    other = add_user(world, db, password_hash, "gestor2", "manager", world.area)
    intruder = client_for(other)
    assert intruder.get(f"{API}/manager/modules/{world.mods[0].id}").status_code == 403
    assert intruder.put(f"{API}/manager/modules/{world.mods[0].id}", json=module_payload(status="published"), headers=csrf(intruder)).status_code == 403
    assert client_for(world.mgr).get(f"{API}/manager/modules/{world.foreign.id}").status_code == 404


def test_manager_creates_and_edits_challenges(world, client_for):
    manager = client_for(world.mgr)
    r = manager.post(f"{API}/manager/challenges", json=challenge_payload(status="draft"), headers=csrf(manager))
    assert r.status_code == 200 and r.json()["status"] == "draft"
    challenge_id = r.json()["id"]
    assert manager.get(f"{API}/manager/challenges/{challenge_id}").json()["correct_index"] == 1
    assert manager.put(f"{API}/manager/challenges/{challenge_id}", json=challenge_payload(correct_index=2), headers=csrf(manager)).status_code == 200


def test_challenge_validation_rejects_missing_correct_option(world, client_for):
    manager = client_for(world.mgr)
    r = manager.post(f"{API}/manager/challenges", json=challenge_payload(correct_index=3), headers=csrf(manager))
    assert r.status_code == 422


# ---------------------------------------------------------------- HU-09 asignar y fechas límite

def test_module_assigned_to_an_area_is_hidden_from_other_areas(world, client_for, db, password_hash):
    ventas = add_area(world, db, "Ventas")
    seller = add_user(world, db, password_hash, "vendedora", "worker", ventas)
    manager = client_for(world.mgr)
    target = world.mods[0]
    r = manager.post(f"{API}/manager/assignments", json={"item_type": "module", "item_id": target.id, "target": "area",
                                                        "area_id": world.area.id, "due_at": in_days(7)}, headers=csrf(manager))
    assert r.status_code == 200

    finance = client_for(world.w1)
    assert finance.get(f"{API}/worker/modules/{target.id}").status_code == 200
    due = {m["id"]: m["due"] for m in finance.get(f"{API}/worker/dashboard").json()["modules"]}[target.id]
    assert due.startswith("Vence el")

    sales = client_for(seller)
    assert sales.get(f"{API}/worker/modules/{target.id}").status_code == 404
    assert target.id not in {m["id"] for m in sales.get(f"{API}/worker/dashboard").json()["modules"]}
    assert sales.get(f"{API}/worker/modules/{world.mods[1].id}").status_code == 200       # sin asignación sigue visible


def test_closest_deadline_wins_when_several_assignments_apply(world, client_for):
    manager = client_for(world.mgr)
    target = world.mods[1]
    manager.post(f"{API}/manager/assignments", json={"item_type": "module", "item_id": target.id, "target": "company",
                                                    "due_at": in_days(30)}, headers=csrf(manager))
    manager.post(f"{API}/manager/assignments", json={"item_type": "module", "item_id": target.id, "target": "user",
                                                    "user_id": world.w1.id, "due_at": in_days(2)}, headers=csrf(manager))
    soon = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%d/%m/%Y")
    due = {m["id"]: m["due"] for m in client_for(world.w1).get(f"{API}/worker/dashboard").json()["modules"]}[target.id]
    assert due == f"Vence el {soon}"


def test_assignment_rules_are_enforced(world, client_for):
    manager = client_for(world.mgr)
    post = lambda body: manager.post(f"{API}/manager/assignments", json=body, headers=csrf(manager))
    assert post({"item_type": "module", "item_id": world.mods[0].id, "target": "area"}).status_code == 422          # sin área
    assert post({"item_type": "module", "item_id": world.mods[0].id, "target": "company", "area_id": 1}).status_code == 422
    assert post({"item_type": "module", "item_id": world.mods[0].id, "target": "company",
                 "due_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}).status_code == 422        # fecha pasada
    assert post({"item_type": "module", "item_id": world.draft.id, "target": "company"}).status_code == 422       # borrador
    assert post({"item_type": "module", "item_id": world.foreign.id, "target": "company"}).status_code == 404      # otra empresa
    assert post({"item_type": "module", "item_id": world.mods[0].id, "target": "user", "user_id": world.adm.id}).status_code == 404


def test_only_the_author_can_remove_an_assignment(world, client_for, db, password_hash):
    manager = client_for(world.mgr)
    assignment = manager.post(f"{API}/manager/assignments", json={"item_type": "module", "item_id": world.mods[0].id,
                                                                  "target": "company"}, headers=csrf(manager)).json()["id"]
    other = add_user(world, db, password_hash, "gestor3", "manager", world.area)
    intruder = client_for(other)
    assert intruder.delete(f"{API}/manager/assignments/{assignment}", headers=csrf(intruder)).status_code == 404
    assert manager.delete(f"{API}/manager/assignments/{assignment}", headers=csrf(manager)).status_code == 200
    assert manager.get(f"{API}/manager/assignments").json() == []


def test_challenge_assigned_to_an_area_cannot_be_answered_by_others(world, client_for, db, password_hash):
    ventas = add_area(world, db, "Ventas")
    seller = add_user(world, db, password_hash, "vendedor", "worker", ventas)
    manager = client_for(world.mgr)
    manager.post(f"{API}/manager/assignments", json={"item_type": "challenge", "item_id": world.c1.id, "target": "area",
                                                    "area_id": world.area.id}, headers=csrf(manager))
    sales = client_for(seller)
    assert sales.post(f"{API}/worker/challenges/{world.c1.id}/answer", json={"choice": 1}, headers=csrf(sales)).status_code == 404
    finance = client_for(world.w1)
    assert finance.post(f"{API}/worker/challenges/{world.c1.id}/answer", json={"choice": 1}, headers=csrf(finance)).status_code == 200


# ---------------------------------------------------------------- HU-10 estadísticas

def test_stats_show_each_worker_for_own_content_only(world, client_for):
    worker = client_for(world.w1)
    worker.post(f"{API}/worker/modules/{world.mods[0].id}/complete", headers=csrf(worker))
    answer = worker.post(f"{API}/worker/challenges/{world.c1.id}/answer", json={"choice": 1}, headers=csrf(worker))
    assert answer.status_code == 200
    stats = client_for(world.mgr).get(f"{API}/manager/stats").json()

    module = next(m for m in stats["modules"] if m["id"] == world.mods[0].id)
    assert module["audience"] == 2 and module["completed"] == 1 and module["completion_rate"] == 50
    done = {row["user_id"]: row["completed"] for row in module["workers"]}
    assert done == {world.w1.id: True, world.w2.id: False}

    assert world.foreign.id not in {m["id"] for m in stats["modules"]}
    challenge = next(c for c in stats["challenges"] if c["id"] == world.c1.id)
    assert challenge["attempts"] == 1 and challenge["correct"] == 1 and challenge["success_rate"] == 100


def test_dashboard_topic_errors_expose_the_rate_for_the_front(world, client_for):
    worker = client_for(world.w1)
    worker.post(f"{API}/worker/challenges/{world.c2.id}/answer", json={"choice": 0}, headers=csrf(worker))
    dash = client_for(world.mgr).get(f"{API}/manager/dashboard").json()
    top = dash["topicErrors"][0]
    assert top["topic"] == "Phishing" and top["errorRate"] == 100 and top["error_rate"] == 100


def test_manager_dashboard_lists_modules_and_challenges_apart(world, client_for):
    dash = client_for(world.mgr).get(f"{API}/manager/dashboard").json()
    assert {c["id"] for c in dash["challenges"]} == {world.c1.id, world.c2.id}
    assert all(row["editable"] for row in dash["content"] if row["id"] in {m.id for m in world.mods})
    assert all(row["kind"] == "challenge" for row in dash["challenges"])
    assert world.foreign.id not in {row["id"] for row in dash["content"]}
    stats_row = next(r for r in dash["content"] if r["id"] == world.draft.id)
    assert stats_row["status"] == "Borrador" and stats_row["editable"] is True


# ---------------------------------------------------------------- retos del trabajador

def test_demo_seed_creates_two_published_challenges_once(world, client_for, db):
    from app.demo_challenges import DEMO_CHALLENGES, ensure_demo_challenges
    assert len(DEMO_CHALLENGES) == 2
    assert ensure_demo_challenges(db, world.co, world.mgr) == 2
    assert ensure_demo_challenges(db, world.co, world.mgr) == 0          # no duplica al repetir
    titles = {c["title"] for c in client_for(world.w1).get(f"{API}/worker/dashboard").json()["challenges"]}
    assert {d["title"] for d in DEMO_CHALLENGES} <= titles


def test_worker_challenge_list_marks_answered_ones(world, client_for):
    worker = client_for(world.w1)
    worker.post(f"{API}/worker/challenges/{world.c1.id}/answer", json={"choice": 1}, headers=csrf(worker))
    rows = {c["id"]: c for c in worker.get(f"{API}/worker/dashboard").json()["challenges"]}
    assert rows[world.c1.id]["answered"] is True and rows[world.c1.id]["is_correct"] is True
    assert rows[world.c2.id]["answered"] is False and rows[world.c2.id]["is_correct"] is None
