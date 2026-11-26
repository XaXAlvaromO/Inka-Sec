from sqlalchemy.orm import Session
from app.models.models import AuditLog, User

def record_audit(db: Session, *, action: str, result: str, user: User | None = None, ip: str | None = None, user_agent: str | None = None, details: dict | None = None, company_id: int | None = None):
    # company_id solo hace falta cuando el actor y la empresa afectada no son la misma, como
    # cuando el superadministrador actúa sobre una empresa cliente: así el hecho queda también
    # en la auditoría de esa empresa, no solo en la de la plataforma.
    row = AuditLog(company_id=company_id if company_id is not None else (user.company_id if user else None), user_id=user.id if user else None, action=action, result=result, ip_address=ip, user_agent=(user_agent or "")[:255], details=details)
    db.add(row)
    db.commit()
    return row
