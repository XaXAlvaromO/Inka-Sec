from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.models import Area, ModuleProgress, User


def admin_report_summary(db: Session, company_id: int) -> dict:
    area_rows = db.execute(
        select(
            Area.id,
            Area.name,
            func.count(User.id),
            func.sum(case((User.is_active.is_(True), 1), else_=0)),
        )
        .outerjoin(User, and_(User.area_id == Area.id, User.company_id == company_id))
        .where(Area.company_id == company_id)
        .group_by(Area.id, Area.name)
        .order_by(Area.name)
    ).all()
    progress_rows = db.execute(
        select(
            User.area_id,
            func.avg(ModuleProgress.progress),
            func.sum(case((ModuleProgress.progress >= 100, 1), else_=0)),
        )
        .join(ModuleProgress, ModuleProgress.user_id == User.id)
        .where(User.company_id == company_id)
        .group_by(User.area_id)
    ).all()
    progress_by_area = {area_id: (average, completed) for area_id, average, completed in progress_rows}
    areas = []
    for area_id, name, users, active_users in area_rows:
        average, completed = progress_by_area.get(area_id, (None, 0))
        areas.append({
            "id": area_id,
            "name": name,
            "users": users,
            "active_users": active_users or 0,
            "average_progress": round(average) if average is not None else None,
            "completed_modules": completed or 0,
        })
    total_users, active_users = db.execute(
        select(func.count(User.id), func.sum(case((User.is_active.is_(True), 1), else_=0)))
        .where(User.company_id == company_id)
    ).one()
    overall_average, total_completed = db.execute(
        select(
            func.avg(ModuleProgress.progress),
            func.sum(case((ModuleProgress.progress >= 100, 1), else_=0)),
        )
        .join(User, User.id == ModuleProgress.user_id)
        .where(User.company_id == company_id)
    ).one()
    return {
        "total_users": total_users,
        "active_users": active_users or 0,
        "average_progress": round(overall_average) if overall_average is not None else None,
        "completed_modules": total_completed or 0,
        "areas": areas,
    }
