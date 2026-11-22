"""Formatos de reto: escenario por pasos y encuentra las señales. Y la columna nueva en bases existentes."""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.db.migrate import ensure_columns
from conftest import API, csrf

STEPS = [
    {"prompt": "Te piden instalar un programa de acceso remoto.", "options": [
        {"text": "Lo instalo", "feedback": "El atacante controla tu equipo.", "safe": False},
        {"text": "Verifico con soporte oficial", "feedback": "Bien: canal que tú eliges.", "safe": True}]},
    {"prompt": "Insiste con un número de ticket.", "options": [
        {"text": "Cuelgo y llamo al número oficial", "feedback": "Rompes el engaño.", "safe": True},
        {"text": "Sigo sus pasos", "feedback": "El ticket es parte del guion.", "safe": False},
        {"text": "Pido que lo envíe por correo", "feedback": "El mismo riesgo por otro canal.", "safe": False}]},
]
SEGMENTS = [
    {"field": "from", "text": "Soporte <a@micros0ft.com>", "suspicious": True, "explanation": "Dominio falso con un cero."},
    {"field": "subject", "text": "Tu cuenta será suspendida", "suspicious": True, "explanation": "Urgencia y amenaza."},
    {"field": "body", "text": "Si tienes dudas, llama a la mesa de ayuda.", "suspicious": False, "explanation": "Frase normal."},
    {"field": "link", "text": "http://login.verificar.co", "suspicious": True, "explanation": "Enlace no oficial."},
]


def payload(kind, **changes):
    body = {"title": f"Reto {kind}", "topic": "Phishing", "kind": kind, "status": "published",
            "scenario": "Llega este mensaje a tu bandeja de entrada a primera hora.", "feedback": "Verifica y reporta."}
    if kind == "steps":
        body["steps"] = STEPS
    if kind == "signals":
        body["segments"] = SEGMENTS
    body.update(changes)
    return body


def create(manager, body):
    return manager.post(f"{API}/manager/challenges", json=body, headers=csrf(manager))


def answer(worker, cid, **body):
    return worker.post(f"{API}/worker/challenges/{cid}/answer", json=body, headers=csrf(worker))


def test_steps_challenge_flow(world, client_for):
    manager = client_for(world.mgr)
    r = create(manager, payload("steps"))
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    worker = client_for(world.w1)
    row = next(c for c in worker.get(f"{API}/worker/dashboard").json()["challenges"] if c["id"] == cid)
    assert row["kind"] == "steps" and len(row["steps"]) == 2
    assert "safe" not in str(row) and "feedback" not in str(row["steps"])          # sin respuestas antes de jugar

    check = worker.post(f"{API}/worker/challenges/{cid}/check", json={"step": 0, "choice": 0}, headers=csrf(worker)).json()
    assert check["safe"] is False and check["safe_index"] == 1 and "controla" in check["feedback"]

    r = answer(worker, cid, choices=[0, 0])
    body = r.json()
    assert r.status_code == 200 and body["is_correct"] is False and body["score"] == 50 and body["safe_steps"] == 1
    assert answer(worker, cid, choices=[1, 0]).json()["is_correct"] is True
    assert answer(worker, cid, choices=[1]).status_code == 422                     # faltan pasos
    assert answer(worker, cid, choices=[1, 7]).status_code == 422


def test_signals_challenge_scores_found_minus_false_marks(world, client_for):
    cid = create(client_for(world.mgr), payload("signals")).json()["id"]
    worker = client_for(world.w1)
    row = next(c for c in worker.get(f"{API}/worker/dashboard").json()["challenges"] if c["id"] == cid)
    assert row["segments"][0] == {"field": "from", "text": "Soporte <a@micros0ft.com>"}
    assert "suspicious" not in str(row)

    body = answer(worker, cid, marked=[0, 1, 2]).json()          # 2 señales y 1 marca equivocada de 3 señales
    assert body["found"] == 2 and body["false_marks"] == 1 and body["score"] == 33 and body["is_correct"] is False
    assert body["segments"][3]["suspicious"] is True and body["segments"][3]["marked"] is False
    perfect = answer(worker, cid, marked=[0, 1, 3]).json()
    assert perfect["is_correct"] is True and perfect["score"] == 100 and perfect["tries"] == 2
    assert answer(worker, cid, marked=[9]).status_code == 422


@pytest.mark.parametrize("kind, changes", [
    ("steps", {"steps": STEPS[:1]}),                                                         # un solo paso
    ("steps", {"steps": [{**STEPS[0], "options": [{**o, "safe": True} for o in STEPS[0]["options"]]}, STEPS[1]]}),  # dos seguras
    ("signals", {"segments": SEGMENTS[:2]}),                                                 # muy pocos fragmentos
    ("signals", {"segments": [{**s, "suspicious": False} for s in SEGMENTS]}),             # sin señales
    ("signals", {"segments": [s for s in SEGMENTS if s["field"] != "from"] + [SEGMENTS[2]]}),  # sin remitente
    ("quick", {}),                                                                           # rápido sin opciones
])
def test_invalid_formats_are_rejected(world, client_for, kind, changes):
    assert create(client_for(world.mgr), payload(kind, **changes)).status_code == 422


def test_form_round_trip_and_kind_locked_after_attempts(world, client_for):
    manager = client_for(world.mgr)
    cid = create(manager, payload("signals")).json()["id"]
    form = manager.get(f"{API}/manager/challenges/{cid}").json()
    assert form["kind"] == "signals" and form["segments"][0]["explanation"] == "Dominio falso con un cero."
    worker = client_for(world.w1)
    answer(worker, cid, marked=[0])
    quick = payload("quick", options=["a", "b"], correct_index=0)
    r = manager.put(f"{API}/manager/challenges/{cid}", json=quick, headers=csrf(manager))
    assert r.status_code == 422 and "formato" in r.json()["detail"]
    assert manager.put(f"{API}/manager/challenges/{cid}", json=payload("signals", title="Nuevo título"), headers=csrf(manager)).status_code == 200


def test_missing_columns_are_added_to_an_existing_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:  # tablas como estaban antes de este cambio
        conn.execute(text("CREATE TABLE challenges (id INTEGER PRIMARY KEY, title VARCHAR(180), options JSON, correct_index INTEGER)"))
        conn.execute(text("INSERT INTO challenges (id, title, options, correct_index) VALUES (1, 'viejo', '[\"a\",\"b\"]', 0)"))
        conn.execute(text("CREATE TABLE challenge_attempts (id INTEGER PRIMARY KEY, is_correct BOOLEAN)"))
    added = ensure_columns(engine)
    assert set(added) == {"challenges.kind", "challenges.content", "challenge_attempts.tries",
                          "challenge_attempts.last_correct", "challenge_attempts.last_score"}
    assert {c["name"] for c in inspect(engine).get_columns("challenges")} >= {"kind", "content"}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT kind FROM challenges WHERE id = 1")).scalar() == "quick"   # los retos viejos siguen siendo rápidos
    assert ensure_columns(engine) == []                                                          # segunda vez no hace nada
