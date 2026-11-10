from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.models import User, ModuleProgress, AuditLog, Area, Notification
from app.repositories import module_repository, progress_repository, user_repository
from app.schemas.user import user_row
from app.services import progress_service

def notifications_for(db: Session, user_id: int):
    rows = db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(5)).all()
    return [{"id":n.id,"title":n.title,"body":n.body,"time":"Pendiente" if not n.read_at else "Leída"} for n in rows]

def worker_dashboard(db: Session, user: User):
    mods = module_repository.list_published(db, user.company_id)
    done_ids = set(db.scalars(select(ModuleProgress.module_id).where(ModuleProgress.user_id==user.id, ModuleProgress.completed_at.is_not(None))).all())
    prog = progress_service.worker_progress(db, user)
    module_cards = [{"id":m.id,"title":m.title,"topic":m.topic,"progress":100 if m.id in done_ids else 0,"time":"10-12 min","icon":"book","due":"Sin vencer"} for m in mods]
    pending = progress_repository.next_pending_challenge(db, user)
    return {
      "stats":[
        {"label":"Módulos completados","value":f"{prog['modules']['completed']} / {prog['modules']['total']}","helper":"Ruta COM-B","icon":"book","tone":"blue"},
        {"label":"Retos correctos","value":f"{prog['challenges']['correct']} / {prog['challenges']['total']}","helper":f"{prog['challenges']['answered']} respondidos","icon":"target","tone":"green"},
        {"label":"Progreso general","value":f"{prog['modules']['percent']}%","helper":"Módulos terminados","icon":"chart","tone":"blue"},
        {"label":"Refuerzos","value":"7/30/90","helper":"Días programados","icon":"clock","tone":"amber"}],
      "progress": prog["modules"]["percent"],
      "modules": module_cards,
      "challenge": {"id":pending.id,"title":pending.title,"description":pending.scenario,"points":100,"time":"1 min","due":"Según cronograma"} if pending else None,
      "weakTopics": prog["weak_topics"],
      "notifications": notifications_for(db,user.id)
    }

def manager_dashboard(db: Session, user: User):
    mods = module_repository.list_all(db, user.company_id)
    users_count = user_repository.count_by_company(db, user.company_id)
    stats = progress_service.manager_stats(db, user)
    module_rate = {m["id"]: m["completion_rate"] for m in stats["modules"]}
    attempts = sum(c["attempts"] for c in stats["challenges"]); correct = sum(c["correct"] for c in stats["challenges"])
    rate = progress_service.rate(correct, attempts)
    return {"stats":[
      {"label":"Contenidos publicados","value":str(sum(1 for m in mods if m.status=='published')),"helper":f"{len(mods)} módulos totales","icon":"book","tone":"blue"},
      {"label":"Usuarios alcanzados","value":str(users_count),"helper":"Empresa actual","icon":"users","tone":"blue"},
      {"label":"Tasa de aprobación","value":"--" if rate is None else f"{rate}%","helper":"Aciertos en tus retos" if rate is not None else "Disponible con intentos","icon":"check","tone":"green"},
      {"label":"Pendientes de revisión","value":str(sum(1 for m in mods if m.status!='published')),"helper":"Borradores/programados","icon":"edit","tone":"amber"}],
      "content":[{"id":m.id,"title":m.title,"type":"Módulo","status":"Publicado" if m.status=='published' else m.status.title(),"users":users_count,"success":module_rate.get(m.id),"updated":m.updated_at.isoformat()} for m in mods],
      "topicErrors":stats["topic_errors"],"notifications":notifications_for(db,user.id)}

def admin_dashboard(db: Session, user: User):
    users = user_repository.list_by_company(db, user.company_id)
    areas=db.scalars(select(Area).where(Area.company_id==user.company_id).order_by(Area.name)).all()
    audits=db.scalars(select(AuditLog).where(AuditLog.company_id==user.company_id).order_by(AuditLog.created_at.desc()).limit(8)).all()
    rows=progress_service.company_progress(db, user.company_id)
    overall=progress_service.summarize(rows) if rows else None
    progress_by_user={r["user_id"]: r["modules_percent"] for r in rows}
    area_stats=progress_service.by_area(rows)
    return {"stats":[
      {"label":"Usuarios activos","value":str(sum(1 for u in users if u.is_active)),"helper":f"{len(users)} registrados","icon":"users","tone":"blue"},
      {"label":"Cumplimiento global","value":f"{overall['modules_percent']}%" if overall else "--","helper":"Módulos aprobados" if overall else "Disponible con progreso","icon":"chart","tone":"green"},
      {"label":"2FA en roles críticos","value":"100%","helper":"Gestores y administradores","icon":"lock","tone":"blue"},
      {"label":"Eventos de auditoría","value":str(len(audits)),"helper":"Actividad reciente","icon":"audit","tone":"amber"}],
      "users":[{**user_row(u),"progress":progress_by_user.get(u.id,0)} for u in users],
      "audit":[{"id":a.id,"type":"danger" if a.result!='success' else "success","action":a.action,"detail":f"IP {a.ip_address or '-'}","time":a.created_at.isoformat()} for a in audits],
      "areas":[{"name":a.name,"compliance":area_stats.get(a.name,{}).get("modules_percent",0),"users":sum(1 for u in users if u.area_id==a.id)} for a in areas],
      "notifications":notifications_for(db,user.id)}
