from sqlalchemy.orm import Session
from app.models.models import AuditLog, User

def record_audit(db: Session, *, action: str, result: str, user: User | None = None, ip: str | None = None, user_agent: str | None = None, details: dict | None = None):
    row = AuditLog(company_id=user.company_id if user else None, user_id=user.id if user else None, action=action, result=result, ip_address=ip, user_agent=(user_agent or "")[:255], details=details)
    db.add(row)
    db.commit()
    return row
