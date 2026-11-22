"""Certificados por tema (RF-07): regla del 80 %, vigencia de 12 meses, renovación y verificación pública."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.models import Certificate, LearningModule, utcnow
from conftest import API, csrf

QUESTIONS = [
    {"prompt": "¿Qué haces con un enlace raro?", "options": ["Lo abro", "Lo reviso antes"], "correct": 1, "feedback": "Revisa."},
    {"prompt": "¿Quién pide tu clave?", "options": ["Nadie legítimo", "Soporte"], "correct": 0, "feedback": "Nadie."},
    {"prompt": "¿Qué haces si dudas?", "options": ["Reporto", "Ignoro"], "correct": 0, "feedback": "Reporta."},
    {"prompt": "¿Urgencia es señal?", "options": ["Sí", "No"], "correct": 0, "feedback": "Sí."},
    {"prompt": "¿Verificas por otro canal?", "options": ["No", "Sí"], "correct": 1, "feedback": "Sí."},
]
RIGHT = [q["correct"] for q in QUESTIONS]


@pytest.fixture
def phishing(world, db):
    """Dos módulos de Phishing con 5 preguntas cada uno (80 % = 4 de 5)."""
    mods = []
    for slug in ("phish-1", "phish-2"):
        m = LearningModule(company_id=world.co.id, slug=slug, title=f"Módulo {slug}", topic="Phishing", behavior_objective="x",
                           status="published", content_json={"title": slug, "capacity_questions": QUESTIONS}, created_by=world.mgr.id)
        db.add(m); mods.append(m)
    db.commit()
    return mods


def grade(client, module, choices):
    answers = [{"index": i, "choice": c} for i, c in enumerate(choices)]
    return client.post(f"{API}/worker/modules/{module.id}/capacity", json={"answers": answers}, headers=csrf(client))


def complete(client, module):
    return client.post(f"{API}/worker/modules/{module.id}/complete", headers=csrf(client))


def topic(overview, name):
    return next(t for t in overview["topics"] if t["topic"] == name)


def pass_phishing(client, phishing):
    for m in phishing:
        assert grade(client, m, RIGHT).status_code == 200
        r = complete(client, m)
    return r


def test_certificate_needs_every_module_of_the_topic_at_80_percent(world, phishing, client_for):
    worker = client_for(world.w1)
    almost = RIGHT[:3] + [1 - RIGHT[3], 1 - RIGHT[4]]            # 3 de 5 = 60 %
    assert grade(worker, phishing[0], almost).json()["percent"] == 60
    complete(worker, phishing[0])
    grade(worker, phishing[1], RIGHT); complete(worker, phishing[1])
    state = topic(worker.get(f"{API}/worker/certificates").json(), "Phishing")
    assert state["certificate"] is None and state["passed"] == 1 and state["total"] == 2
    assert next(m for m in state["modules"] if m["id"] == phishing[0].id)["needs_review"] is True

    # Repetir el módulo no castiga: se guarda el mejor intento y el certificado llega al aprobar.
    r = grade(worker, phishing[0], RIGHT[:4] + [1 - RIGHT[4]])  # 4 de 5 = 80 %
    assert r.json()["percent"] == 80 and r.json()["new_certificates"] == ["Phishing"]
    cert = topic(worker.get(f"{API}/worker/certificates").json(), "Phishing")["certificate"]
    assert cert["status"] == "active" and cert["code"].startswith("INKA-") and cert["days_left"] >= 364
    assert sorted(cert["modules"]) == ["Módulo phish-1", "Módulo phish-2"]


def test_completing_the_last_module_issues_the_certificate(world, phishing, client_for):
    worker = client_for(world.w1)
    grade(worker, phishing[0], RIGHT); complete(worker, phishing[0])
    grade(worker, phishing[1], RIGHT)
    assert complete(worker, phishing[1]).json()["new_certificates"] == ["Phishing"]
    assert complete(worker, phishing[1]).json()["new_certificates"] == []   # no se duplica


def test_certificate_is_private_to_its_owner(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id))
    other = client_for(world.w2)
    assert other.get(f"{API}/worker/certificates/{cert.id}/pdf").status_code == 404
    assert other.get(f"{API}/worker/certificates/{cert.id}/renewal").status_code == 404
    assert client_for(world.mgr).get(f"{API}/worker/certificates").status_code == 403


def test_pdf_is_downloadable_and_has_no_score(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id))
    r = worker.get(f"{API}/worker/certificates/{cert.id}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and cert.code in r.headers["content-disposition"]


def test_public_verification(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id))
    anonymous = client_for()
    body = anonymous.get(f"{API}/certificates/verify/{cert.code.lower()}").json()
    assert body["valid"] is True and body["holder"] == "ana" and body["topic"] == "Phishing" and body["company"] == "A"
    assert "score" not in body and "percent" not in body
    assert anonymous.get(f"{API}/certificates/verify/INKA-AAAA-BBBB-CCCC").status_code == 404
    assert anonymous.get(f"{API}/certificates/verify/<script>").status_code in {404, 422}


def _age(db, cert, days_left):
    cert = db.get(Certificate, cert.id)
    cert.expires_at = utcnow() + timedelta(days=days_left)
    cert.issued_at = cert.expires_at - timedelta(days=365)
    db.commit()
    return cert


def test_renewal_opens_30_days_before_and_needs_80_percent(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id))
    assert worker.get(f"{API}/worker/certificates/{cert.id}/renewal").status_code == 409   # aún falta mucho

    _age(db, cert, 20)
    dash = worker.get(f"{API}/worker/dashboard").json()
    assert any("vence pronto" in n["title"] for n in dash["notifications"])
    quiz = worker.get(f"{API}/worker/certificates/{cert.id}/renewal").json()
    assert len(quiz["questions"]) == 10 and "correct" not in str(quiz["questions"])

    keys = [q["key"] for q in quiz["questions"]]
    wrong = [{"key": k, "choice": 1 - RIGHT[i % 5]} for i, k in enumerate(keys)]
    r = worker.post(f"{API}/worker/certificates/{cert.id}/renewal", json={"answers": wrong}, headers=csrf(worker))
    assert r.status_code == 200 and r.json()["passed"] is False and r.json()["certificate"] is None   # se puede reintentar

    right = [{"key": k, "choice": RIGHT[i % 5]} for i, k in enumerate(keys)]
    r = worker.post(f"{API}/worker/certificates/{cert.id}/renewal", json={"answers": right}, headers=csrf(worker))
    body = r.json()
    assert body["passed"] is True and body["certificate"]["status"] == "active" and body["certificate"]["code"] != cert.code
    overview = worker.get(f"{API}/worker/certificates").json()
    assert topic(overview, "Phishing")["certificate"]["renewed"] is True
    assert [h["status"] for h in overview["history"]] == ["superseded"]
    assert client_for().get(f"{API}/certificates/verify/{cert.code}").json()["valid"] is False   # el antiguo ya no vale


def test_expired_certificate_is_not_reissued_by_old_modules(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id))
    _age(db, cert, -1)
    state = topic(worker.get(f"{API}/worker/certificates").json(), "Phishing")
    assert state["certificate"]["status"] == "expired" and state["certificate"]["can_renew"] is True
    assert db.scalar(select(Certificate.id).where(Certificate.user_id == world.w1.id, Certificate.id != cert.id)) is None


def test_renewal_rejects_incomplete_answers(world, phishing, client_for, db):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    cert = _age(db, db.scalar(select(Certificate).where(Certificate.user_id == world.w1.id)), 5)
    quiz = worker.get(f"{API}/worker/certificates/{cert.id}/renewal").json()
    partial = [{"key": quiz["questions"][0]["key"], "choice": 0}]
    assert worker.post(f"{API}/worker/certificates/{cert.id}/renewal", json={"answers": partial}, headers=csrf(worker)).status_code == 422


def test_manager_sees_certificate_counts_not_scores(world, phishing, client_for):
    worker = client_for(world.w1)
    pass_phishing(worker, phishing)
    stats = client_for(world.mgr).get(f"{API}/manager/stats").json()
    row = next(c for c in stats["certificates"] if c["topic"] == "Phishing")
    assert row["active"] == 1 and row["workers"] == 2
    people = {w["user_id"]: w["certificates"] for w in stats["workers"]}
    assert people[world.w1.id] == 1 and people[world.w2.id] == 0
    assert "score" not in str(stats["modules"])
