"""Certificados por tema (RF-07).

Regla para obtenerlo, por cada tema:
- completar TODOS los módulos publicados de ese tema que la persona tiene visibles, y
- tener al menos 80 % en las preguntas de capacidad de cada uno.
Completar un módulo exige pasar por el paso de acción real, así que también queda registrada.

Vigencia: 12 meses desde la emisión (como la capacitación anual de PCI DSS 12.6).
Renovación: un repaso corto con las preguntas de capacidad del tema (80 % para aprobar),
disponible desde 30 días antes del vencimiento. Se puede reintentar sin límite.

El certificado dice "Aprobado": nunca muestra el puntaje ni cuántos intentos tomó.
Los retos no cuentan para el certificado (entrenan, no califican).
"""
from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Certificate, Company, LearningModule, ModuleProgress, User, utcnow
from app.repositories import module_repository
from app.services import visibility

PASS_PERCENT = 80
VALIDITY_DAYS = 365
WARNING_DAYS = 30
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para que se lea sin errores

STATUS_LABEL = {"active": "Vigente", "expiring": "Por vencer", "expired": "Vencido", "superseded": "Reemplazado"}


class NotFound(Exception): ...
class NotRenewable(Exception): ...
class InvalidAnswers(Exception): ...


def new_code() -> str:
    chunks = ["".join(secrets.choice(CODE_ALPHABET) for _ in range(4)) for _ in range(3)]
    return "INKA-" + "-".join(chunks)


def status_of(cert: Certificate, now: datetime | None = None) -> str:
    now = now or utcnow()
    if cert.superseded_at is not None:
        return "superseded"
    expires = visibility.aware(cert.expires_at)
    if expires <= now:
        return "expired"
    if expires - now <= timedelta(days=WARNING_DAYS):
        return "expiring"
    return "active"


def days_left(cert: Certificate, now: datetime | None = None) -> int:
    now = now or utcnow()
    return (visibility.aware(cert.expires_at) - now).days


def _topic_modules(db: Session, user: User) -> dict[str, list[LearningModule]]:
    """Módulos publicados y visibles para esta persona, agrupados por tema."""
    visible = visibility.visible_items(db, user, "module")
    groups: dict[str, list[LearningModule]] = defaultdict(list)
    for module in module_repository.list_published(db, user.company_id):
        if module.id in visible:
            groups[module.topic].append(module)
    return groups


def _module_results(db: Session, user: User) -> dict[int, ModuleProgress]:
    rows = db.scalars(select(ModuleProgress).where(ModuleProgress.user_id == user.id)).all()
    return {row.module_id: row for row in rows}


def module_passed(module: LearningModule, progress: ModuleProgress | None) -> bool:
    """Completado y con 80 % o más en sus preguntas de capacidad (si el módulo no tiene preguntas, basta completarlo)."""
    if not progress or progress.completed_at is None:
        return False
    if not module.content_json.get("capacity_questions"):
        return True
    return (progress.score or 0) >= PASS_PERCENT


def _current(db: Session, user: User) -> dict[str, Certificate]:
    """El certificado vigente o vencido (no reemplazado) de cada tema."""
    rows = db.scalars(select(Certificate).where(Certificate.user_id == user.id, Certificate.superseded_at.is_(None))).all()
    return {cert.topic: cert for cert in rows}


def _issue(db: Session, user: User, topic: str, modules: list[LearningModule], renewed: bool = False) -> Certificate:
    now = utcnow()
    code = new_code()
    while db.scalar(select(Certificate.id).where(Certificate.code == code)):
        code = new_code()
    cert = Certificate(company_id=user.company_id, user_id=user.id, topic=topic, code=code,
                       module_titles=[m.title for m in modules], issued_at=now,
                       expires_at=now + timedelta(days=VALIDITY_DAYS), renewed=renewed)
    db.add(cert)
    return cert


def sync(db: Session, user: User) -> list[Certificate]:
    """Emite los certificados que la persona ya ganó. Devuelve los nuevos.

    Un tema que ya tiene certificado (vigente o vencido) no se vuelve a emitir solo:
    después del vencimiento se renueva con el repaso, no completando módulos viejos.
    """
    if user.role != "worker":
        return []
    current = _current(db, user)
    results = _module_results(db, user)
    issued = []
    for topic, modules in _topic_modules(db, user).items():
        if topic in current or not modules:
            continue
        if all(module_passed(m, results.get(m.id)) for m in modules):
            issued.append(_issue(db, user, topic, modules))
    if issued:
        db.commit()
    return issued


def certificate_row(cert: Certificate, now: datetime | None = None) -> dict:
    status = status_of(cert, now)
    return {
        "id": cert.id, "topic": cert.topic, "code": cert.code, "status": status, "status_label": STATUS_LABEL[status],
        "issued_at": visibility.aware(cert.issued_at).isoformat(), "expires_at": visibility.aware(cert.expires_at).isoformat(),
        "days_left": days_left(cert, now), "modules": list(cert.module_titles or []), "renewed": cert.renewed,
        "can_renew": status in {"expiring", "expired"},
    }


def worker_overview(db: Session, user: User) -> dict:
    """Certificados de la persona y lo que le falta en cada tema."""
    new = sync(db, user)
    now = utcnow()
    current = _current(db, user)
    results = _module_results(db, user)
    topics = []
    for topic, modules in sorted(_topic_modules(db, user).items()):
        items = []
        for m in modules:
            p = results.get(m.id)
            completed = bool(p and p.completed_at is not None)
            items.append({"id": m.id, "title": m.title, "completed": completed,
                          "passed": module_passed(m, p), "needs_review": completed and not module_passed(m, p)})
        cert = current.get(topic)
        topics.append({"topic": topic, "modules": items, "passed": sum(i["passed"] for i in items), "total": len(items),
                       "certificate": certificate_row(cert, now) if cert else None})
    history = db.scalars(select(Certificate).where(Certificate.user_id == user.id, Certificate.superseded_at.is_not(None))
                         .order_by(Certificate.issued_at.desc())).all()
    return {"pass_percent": PASS_PERCENT, "validity_days": VALIDITY_DAYS, "warning_days": WARNING_DAYS,
            "topics": topics, "history": [certificate_row(c, now) for c in history],
            "new": [c.topic for c in new]}


def summary_for_dashboard(db: Session, user: User) -> dict:
    overview = worker_overview(db, user)
    certs = [t["certificate"] for t in overview["topics"] if t["certificate"]]
    pending = [t for t in overview["topics"] if not t["certificate"]]
    pending.sort(key=lambda t: t["total"] - t["passed"])
    nxt = pending[0] if pending else None
    return {"active": sum(1 for c in certs if c["status"] in {"active", "expiring"}), "topics": len(overview["topics"]),
            "expiring": [c for c in certs if c["status"] == "expiring"], "expired": [c for c in certs if c["status"] == "expired"],
            "next": {"topic": nxt["topic"], "remaining": nxt["total"] - nxt["passed"]} if nxt else None}


def notifications(db: Session, user: User) -> list[dict]:
    """Avisos calculados: certificados por vencer (30 días) y vencidos."""
    out = []
    now = utcnow()
    for cert in _current(db, user).values():
        status = status_of(cert, now)
        if status == "expiring":
            out.append({"id": f"cert-{cert.id}", "title": f"Tu certificado de {cert.topic} vence pronto",
                        "body": f"Vence en {max(days_left(cert, now), 0)} días. Renuévalo con un repaso corto.", "time": "Pendiente"})
        elif status == "expired":
            out.append({"id": f"cert-{cert.id}", "title": f"Tu certificado de {cert.topic} venció",
                        "body": "Haz el repaso del tema para renovarlo.", "time": "Pendiente"})
    return out


# ---------- Renovación ----------

def _owned(db: Session, user: User, cert_id: int) -> Certificate:
    cert = db.get(Certificate, cert_id)
    if not cert or cert.user_id != user.id:
        raise NotFound("Certificado no encontrado")
    return cert


def _renewal_bank(db: Session, user: User, topic: str) -> tuple[list[LearningModule], list[tuple[str, dict]]]:
    modules = _topic_modules(db, user).get(topic, [])
    bank = []
    for m in modules:
        for index, q in enumerate(m.content_json.get("capacity_questions", [])):
            bank.append((f"{m.id}:{index}", q))
    return modules, bank


def renewal_quiz(db: Session, user: User, cert_id: int) -> dict:
    cert = _owned(db, user, cert_id)
    if status_of(cert) not in {"expiring", "expired"}:
        raise NotRenewable(f"Podrás renovarlo desde {WARNING_DAYS} días antes de que venza")
    _, bank = _renewal_bank(db, user, cert.topic)
    if not bank:
        raise NotRenewable("Este tema ya no tiene módulos publicados para repasar")
    return {"certificate": certificate_row(cert), "pass_percent": PASS_PERCENT,
            "questions": [{"key": key, "prompt": q.get("prompt", ""), "options": list(q.get("options", []))} for key, q in bank]}


def renew(db: Session, user: User, cert_id: int, answers: list[dict]) -> dict:
    cert = _owned(db, user, cert_id)
    if status_of(cert) not in {"expiring", "expired"}:
        raise NotRenewable(f"Podrás renovarlo desde {WARNING_DAYS} días antes de que venza")
    modules, bank = _renewal_bank(db, user, cert.topic)
    if not bank:
        raise NotRenewable("Este tema ya no tiene módulos publicados para repasar")
    by_key = {a["key"]: a["choice"] for a in answers}
    if sorted(by_key) != sorted(key for key, _ in bank) or len(answers) != len(bank):
        raise InvalidAnswers("Responde todas las preguntas del repaso")
    results = []
    for key, q in bank:
        options = q.get("options", [])
        choice = by_key[key]
        if not 0 <= choice < len(options):
            raise InvalidAnswers("Opción fuera de rango")
        results.append({"key": key, "is_correct": choice == q.get("correct"), "correct_index": q.get("correct"),
                        "feedback": q.get("feedback", "")})
    correct = sum(r["is_correct"] for r in results)
    percent = round(correct * 100 / len(results))
    passed = percent >= PASS_PERCENT
    new_cert = None
    if passed:
        cert.superseded_at = utcnow()
        new_cert = _issue(db, user, cert.topic, modules, renewed=True)
        db.commit()
    # El porcentaje solo lo ve la propia persona, para saber cuánto le faltó.
    return {"passed": passed, "correct": correct, "total": len(results), "percent": percent, "results": results,
            "certificate": certificate_row(new_cert) if new_cert else None}


# ---------- Verificación pública ----------

def verify(db: Session, code: str) -> dict:
    cert = db.scalar(select(Certificate).where(Certificate.code == code.strip().upper()))
    if not cert:
        raise NotFound("No existe un certificado con ese código")
    user = db.get(User, cert.user_id)
    company = db.get(Company, cert.company_id)
    status = status_of(cert)
    return {"valid": status in {"active", "expiring"}, "status": status, "status_label": STATUS_LABEL[status],
            "holder": user.name if user else "Titular eliminado", "company": company.name if company else "",
            "topic": cert.topic, "issued_at": visibility.aware(cert.issued_at).isoformat(),
            "expires_at": visibility.aware(cert.expires_at).isoformat(), "code": cert.code}


# ---------- Vista del gestor (sin datos individuales de puntaje) ----------

def company_certificates(db: Session, company_id: int, workers: list[User]) -> list[dict]:
    """Por tema: cuántos trabajadores activos tienen el certificado vigente."""
    worker_ids = {w.id for w in workers}
    rows = db.scalars(select(Certificate).where(Certificate.company_id == company_id, Certificate.superseded_at.is_(None))).all()
    by_topic: dict[str, dict] = defaultdict(lambda: {"active": 0, "expiring": 0, "expired": 0})
    now = utcnow()
    for cert in rows:
        if cert.user_id in worker_ids:
            by_topic[cert.topic][status_of(cert, now)] += 1  # la consulta ya excluye los reemplazados
    return [{"topic": topic, **counts, "workers": len(worker_ids)} for topic, counts in sorted(by_topic.items())]


def worker_certificate_count(db: Session, company_id: int) -> dict[int, int]:
    rows = db.scalars(select(Certificate).where(Certificate.company_id == company_id, Certificate.superseded_at.is_(None))).all()
    counts: dict[int, int] = defaultdict(int)
    now = utcnow()
    for cert in rows:
        if status_of(cert, now) in {"active", "expiring"}:
            counts[cert.user_id] += 1
    return counts
