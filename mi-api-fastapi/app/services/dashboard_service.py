from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.models import User, LearningModule, ModuleProgress, AuditLog, Area, Notification

def notifications_for(db: Session, user_id: int):
    rows = db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(5)).all()
    return [{"id":n.id,"title":n.title,"body":n.body,"time":"Pendiente" if not n.read_at else "Leída"} for n in rows]

def worker_dashboard(db: Session, user: User):
    mods = db.scalars(select(LearningModule).where(LearningModule.company_id==user.company_id, LearningModule.status=="published").order_by(LearningModule.id)).all()
    progress_rows = {p.module_id:p for p in db.scalars(select(ModuleProgress).where(ModuleProgress.user_id==user.id)).all()}
    completed = sum(1 for p in progress_rows.values() if p.progress >= 100)
    module_cards=[]
    for m in mods:
        p=progress_rows.get(m.id)
        module_cards.append({"id":m.id,"title":m.title,"topic":m.topic,"progress":p.progress if p else 0,"time":"10-12 min","icon":"book","due":"Sin vencer"})
    overall = round(sum(x["progress"] for x in module_cards)/max(len(module_cards),1))
    return {
      "stats":[
        {"label":"Módulos completados","value":f"{completed} / {len(mods)}","helper":"Ruta COM-B","icon":"book","tone":"blue"},
        {"label":"Retos correctos","value":"--","helper":"Se calcula con intentos","icon":"target","tone":"green"},
        {"label":"Progreso general","value":f"{overall}%","helper":"Promedio actual","icon":"chart","tone":"blue"},
        {"label":"Refuerzos","value":"7/30/90","helper":"Días programados","icon":"clock","tone":"amber"}],
      "progress": overall,
      "modules":module_cards,
      "challenge":{"id":1,"title":"Mini-reto de refuerzo","description":"Escenario breve para comprobar transferencia del aprendizaje.","points":100,"time":"1 min","due":"Según cronograma"},
      "weakTopics":[],
      "notifications":notifications_for(db,user.id)
    }

def manager_dashboard(db: Session, user: User):
    mods=db.scalars(select(LearningModule).where(LearningModule.company_id==user.company_id).order_by(LearningModule.updated_at.desc())).all()
    users_count=db.scalar(select(func.count(User.id)).where(User.company_id==user.company_id)) or 0
    return {"stats":[
      {"label":"Contenidos publicados","value":str(sum(1 for m in mods if m.status=='published')),"helper":f"{len(mods)} módulos totales","icon":"book","tone":"blue"},
      {"label":"Usuarios alcanzados","value":str(users_count),"helper":"Empresa actual","icon":"users","tone":"blue"},
      {"label":"Tasa de aprobación","value":"--","helper":"Disponible con intentos","icon":"check","tone":"green"},
      {"label":"Pendientes de revisión","value":str(sum(1 for m in mods if m.status!='published')),"helper":"Borradores/programados","icon":"edit","tone":"amber"}],
      "content":[{"id":m.id,"title":m.title,"type":"Módulo","status":"Publicado" if m.status=='published' else m.status.title(),"users":users_count,"success":None,"updated":m.updated_at.isoformat()} for m in mods],
      "topicErrors":[],"notifications":notifications_for(db,user.id)}

def admin_dashboard(db: Session, user: User):
    users=db.scalars(select(User).where(User.company_id==user.company_id).order_by(User.id)).all()
    areas=db.scalars(select(Area).where(Area.company_id==user.company_id).order_by(Area.name)).all()
    audits=db.scalars(select(AuditLog).where(AuditLog.company_id==user.company_id).order_by(AuditLog.created_at.desc()).limit(8)).all()
    return {"stats":[
      {"label":"Usuarios activos","value":str(sum(1 for u in users if u.is_active)),"helper":f"{len(users)} registrados","icon":"users","tone":"blue"},
      {"label":"Cumplimiento global","value":"--","helper":"Disponible con progreso","icon":"chart","tone":"green"},
      {"label":"2FA en roles críticos","value":"100%","helper":"Gestores y administradores","icon":"lock","tone":"blue"},
      {"label":"Eventos de auditoría","value":str(len(audits)),"helper":"Actividad reciente","icon":"audit","tone":"amber"}],
      "users":[{"id":u.id,"name":u.name,"email":u.email,"area":u.area.name if u.area else "Sin área","role":{"worker":"Trabajador","manager":"Gestor","admin":"Administrador"}.get(u.role,u.role),"status":"Activo" if u.is_active else "Inactivo","progress":0,"twoFactor":bool(u.totp_secret)} for u in users],
      "audit":[{"id":a.id,"type":"danger" if a.result!='success' else "success","action":a.action,"detail":f"IP {a.ip_address or '-'}","time":a.created_at.isoformat()} for a in audits],
      "areas":[{"name":a.name,"compliance":0,"users":sum(1 for u in users if u.area_id==a.id)} for a in areas],
      "notifications":notifications_for(db,user.id)}
