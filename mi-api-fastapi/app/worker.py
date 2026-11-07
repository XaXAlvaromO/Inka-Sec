import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from app.db.session import SessionLocal
from app.models.models import AuditLog, Notification
from app.core.config import settings

def run_once():
    db=SessionLocal()
    try:
        cutoff=datetime.now(timezone.utc)-timedelta(days=settings.audit_retention_days)
        # RNF exige mínimo 12 meses: solo borra registros MÁS antiguos que la política configurada.
        db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        db.commit()
    finally: db.close()

if __name__ == "__main__":
    while True:
        run_once(); time.sleep(3600)
