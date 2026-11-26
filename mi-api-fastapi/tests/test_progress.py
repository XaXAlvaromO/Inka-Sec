"""Reglas de progreso, vistas a través de las rutas que realmente usa el frontend."""
import pytest
from sqlalchemy import select

from app.models.models import LearningModule
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


def test_challenge_can_be_retried_and_keeps_the_first_attempt(world, client_for, db):
    from app.models.challenge import ChallengeAttempt
    worker = client_for(world.w1)
    assert answer(worker, world.c1, 9).status_code == 422             # opción fuera de rango
    r = answer(worker, world.c1, 0)
    assert r.status_code == 200 and r.json()["is_correct"] is False and r.json()["correct_index"] == 1
    r = answer(worker, world.c1, 1)                                   # el reto entrena: se puede repetir
    assert r.status_code == 200 and r.json()["is_correct"] is True and r.json()["tries"] == 2
    attempt = db.scalar(select(ChallengeAttempt).where(ChallengeAttempt.challenge_id == world.c1.id))
    db.refresh(attempt)
    assert attempt.is_correct is False and attempt.last_correct is True and attempt.tries == 2   # el primero no se pisa
    dash = worker.get(f"{API}/worker/dashboard").json()
    assert dash["challenge"]["id"] == world.c2.id
    assert dash["stats"][1]["value"] == "1 / 2" and dash["stats"][1]["helper"] == "1 resueltos sin errores"
    row = next(c for c in dash["challenges"] if c["id"] == world.c1.id)
    assert row["is_correct"] is True and row["tries"] == 2            # el trabajador ve su práctica
    assert dash["weakTopics"] == [{"name": "Phishing", "icon": "shield", "errors": 1, "score": 0}]


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
    assert dash["stats"][2]["value"] == "--"                            # 1 persona: no se muestran aciertos
    assert dash["topicErrors"] == []


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
    assert created["email"] == "nueva@x.pe" and "totp_setup_secret" not in created and "temporary_password" in created
    new_user = client_for()
    assert new_user.post(f"{API}/auth/login", json={"email": "nueva@x.pe", "password": created["temporary_password"]}).status_code == 200
    assert admin.post(f"{API}/admin/users", json={"name": "Otra", "email": "nueva@x.pe", "area": "Finanzas"}, headers=csrf(admin)).status_code == 409
    assert admin.patch(f"{API}/admin/users/{created['id']}", json={"is_active": False}, headers=csrf(admin)).status_code == 200
    assert new_user.get(f"{API}/auth/me").status_code == 401              # la sesión muere al desactivar
    assert admin.delete(f"{API}/admin/users/{created['id']}", headers=csrf(admin)).status_code == 200
    audit = admin.get(f"{API}/admin/audit", params={"q": "Usuario creado"}).json()
    assert audit["total"] == 1 and audit["items"][0]["action"] == "USER_CREATED"


def test_welcome_email_goes_only_to_new_managers_and_admins(world, client_for):
    from conftest import WELCOME_OUTBOX
    admin = client_for(world.adm)
    for role, label in (("manager", "Gestor"), ("admin", "Administrador")):
        r = admin.post(f"{API}/admin/users", json={"name": f"Nuevo {role}", "email": f"{role}.nuevo@x.pe", "area": "Finanzas", "role": role}, headers=csrf(admin))
        assert r.status_code == 200 and r.json()["email_sent"] is True
        sent = WELCOME_OUTBOX[-1]
        assert sent["to"] == f"{role}.nuevo@x.pe" and sent["role_label"] == label
        assert sent["temporary_password"] == r.json()["temporary_password"]
    n = len(WELCOME_OUTBOX)
    r = admin.post(f"{API}/admin/users", json={"name": "Trabajador", "email": "trab.nuevo@x.pe", "area": "Finanzas", "role": "worker"}, headers=csrf(admin))
    assert r.status_code == 200 and r.json()["email_sent"] is False and len(WELCOME_OUTBOX) == n


def test_user_is_created_even_if_welcome_email_fails(world, client_for, monkeypatch):
    from app.api.routes import admin as admin_routes
    from app.services.email_service import EmailDeliveryError

    def boom(to, **kw): raise EmailDeliveryError("Fallo SMTP")
    monkeypatch.setattr(admin_routes, "send_welcome_email", boom)
    admin = client_for(world.adm)
    r = admin.post(f"{API}/admin/users", json={"name": "Gestora", "email": "gestora@x.pe", "area": "Finanzas", "role": "manager"}, headers=csrf(admin))
    assert r.status_code == 200 and r.json()["email_sent"] is False and r.json()["temporary_password"]
    assert any(u["email"] == "gestora@x.pe" for u in admin.get(f"{API}/admin/users").json())


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
    assert worker.get(f"{API}/worker/modules/{world.mods[0].id}").json() == {"title": "m0", "capacity_questions": [], "reinforcement_days": [7, 30, 90],
        "saved_reflections": {}, "saved_diagnostic": {"C1": 4}, "resume_step": 1}


# ------------------------------------------------- módulo y reto del trabajador

CAPACITY = [
    {"prompt": "¿Cuál es el riesgo de reutilizar la clave?", "options": ["Ninguno", "Que la prueben en otras cuentas", "Nada"],
     "correct": 1, "feedback": "Las credenciales filtradas se prueban en otros servicios."},
    {"prompt": "¿Qué haces con un correo que pide tu clave?", "options": ["La envío", "No la comparto y aviso", "La cambio y la envío"],
     "correct": 1, "feedback": "Nadie legítimo pide tu contraseña."},
]


@pytest.fixture
def lesson(world, db):
    m = LearningModule(company_id=world.co.id, slug="leccion", title="Lección", topic="Credenciales",
                       behavior_objective="x", status="published", content_json={"title": "Lección", "capacity_questions": CAPACITY},
                       created_by=world.mgr.id)
    db.add(m); db.commit()
    return m


def test_worker_never_receives_the_correct_answers(world, lesson, client_for):
    worker = client_for(world.w1)
    body = worker.get(f"{API}/worker/modules/{lesson.id}").json()
    assert len(body["capacity_questions"]) == 2
    for q in body["capacity_questions"]:
        assert set(q) == {"prompt", "options"}
    assert "correct" not in str(body) and "feedback" not in str(body)


def test_capacity_answers_are_graded_on_the_server(world, lesson, client_for):
    worker = client_for(world.w1)
    url = f"{API}/worker/modules/{lesson.id}/capacity"
    r = worker.post(url, json={"answers": [{"index": 0, "choice": 1}, {"index": 1, "choice": 0}]}, headers=csrf(worker))
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] == 1 and body["total"] == 2
    assert body["results"][0]["is_correct"] is True and body["results"][1]["is_correct"] is False
    assert body["results"][1]["correct_index"] == 1 and body["results"][1]["feedback"]


@pytest.mark.parametrize("answers", [
    [{"index": 0, "choice": 1}],                                   # falta una pregunta
    [{"index": 0, "choice": 1}, {"index": 0, "choice": 2}],        # repite una pregunta
    [{"index": 0, "choice": 1}, {"index": 1, "choice": 9}],        # opción inexistente
    [{"index": 0, "choice": 1}, {"index": 25, "choice": 0}],       # pregunta inexistente
])
def test_capacity_rejects_incomplete_or_forged_answers(world, lesson, client_for, answers):
    worker = client_for(world.w1)
    r = worker.post(f"{API}/worker/modules/{lesson.id}/capacity", json={"answers": answers}, headers=csrf(worker))
    assert r.status_code == 422


def test_reflections_are_saved_once_per_question_and_returned(world, lesson, client_for, db):
    from app.models.models import LearningModule, Reflection
    worker = client_for(world.w1)
    url = f"{API}/worker/modules/{lesson.id}/reflections"
    assert worker.post(url, json={"responses": [{"prompt_code": "oportunidad", "text": "El tiempo"}]}, headers=csrf(worker)).status_code == 200
    assert worker.post(url, json={"responses": [{"prompt_code": "oportunidad", "text": "El tiempo y la costumbre"}]}, headers=csrf(worker)).status_code == 200
    rows = db.scalars(select(Reflection).where(Reflection.module_id == lesson.id)).all()
    assert len(rows) == 1 and rows[0].text == "El tiempo y la costumbre"
    detail = worker.get(f"{API}/worker/modules/{lesson.id}").json()
    assert detail["saved_reflections"] == {"oportunidad": "El tiempo y la costumbre"}


def test_comb_responses_are_updated_in_place_not_duplicated(world, client_for, db):
    from app.models.models import CombResponse
    worker = client_for(world.w1)
    url = f"{API}/worker/modules/{world.mods[0].id}/comb"
    payload = {"phase": "pre", "responses": [{"dimension": "capacidad", "code": "C1", "value": 2}]}
    assert worker.post(url, json=payload, headers=csrf(worker)).status_code == 200
    payload["responses"][0]["value"] = 5                                     # el trabajador cambia de opinión
    assert worker.post(url, json=payload, headers=csrf(worker)).status_code == 200
    rows = db.scalars(select(CombResponse).where(CombResponse.module_id == world.mods[0].id, CombResponse.user_id == world.w1.id)).all()
    assert len(rows) == 1 and rows[0].value == 5                             # no quedó una fila duplicada


def test_resume_step_follows_what_is_actually_saved(world, client_for):
    worker = client_for(world.w1)
    module_id = world.mods[0].id
    detail_url = f"{API}/worker/modules/{module_id}"

    assert worker.get(detail_url).json()["resume_step"] == 0                 # primera vez

    worker.post(f"{detail_url}/comb", json={"phase": "pre", "responses": [{"dimension": "capacidad", "code": "C1", "value": 3}]}, headers=csrf(worker))
    body = worker.get(detail_url).json()
    assert body["resume_step"] == 1 and body["saved_diagnostic"] == {"C1": 3}

    worker.post(f"{detail_url}/reflections", json={"responses": [{"prompt_code": "oportunidad", "text": "El tiempo"}]}, headers=csrf(worker))
    assert worker.get(detail_url).json()["resume_step"] == 4

    worker.post(f"{detail_url}/reflections", json={"responses": [{"prompt_code": "motivacion", "text": "Mi familia"}]}, headers=csrf(worker))
    assert worker.get(detail_url).json()["resume_step"] == 5

    assert complete(worker, world.mods[0]).status_code == 200
    assert worker.get(detail_url).json()["resume_step"] == 6                 # ya terminado


def test_reflections_reject_unknown_prompts_and_huge_texts(world, lesson, client_for):
    worker = client_for(world.w1)
    url = f"{API}/worker/modules/{lesson.id}/reflections"
    assert worker.post(url, json={"responses": [{"prompt_code": "otra", "text": "x"}]}, headers=csrf(worker)).status_code == 422
    assert worker.post(url, json={"responses": [{"prompt_code": "motivacion", "text": "x" * 1001}]}, headers=csrf(worker)).status_code == 422


def test_drafts_and_foreign_modules_reject_answers(world, client_for):
    worker = client_for(world.w1)
    for module in (world.draft, world.foreign):
        cap = worker.post(f"{API}/worker/modules/{module.id}/capacity", json={"answers": [{"index": 0, "choice": 0}]}, headers=csrf(worker))
        ref = worker.post(f"{API}/worker/modules/{module.id}/reflections", json={"responses": [{"prompt_code": "oportunidad", "text": "x"}]}, headers=csrf(worker))
        assert cap.status_code == 404 and ref.status_code == 404


def test_pending_challenge_shows_options_but_not_the_answer(world, client_for):
    worker = client_for(world.w1)
    challenge = worker.get(f"{API}/worker/dashboard").json()["challenge"]
    assert challenge["id"] == world.c1.id and challenge["options"] == ["a", "b", "c"]
    assert "correct_index" not in str(challenge)
