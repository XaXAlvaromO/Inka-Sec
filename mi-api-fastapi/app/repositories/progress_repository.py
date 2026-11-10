"""Consultas de progreso. Solo SQL/agregados: ninguna regla de negocio aquí."""
from sqlalchemy import select, func, case, and_
from sqlalchemy.orm import Session, selectinload
from app.models.models import User, LearningModule, ModuleProgress
from app.models.challenge import Challenge, ChallengeAttempt

_correct = func.coalesce(func.sum(case((ChallengeAttempt.is_correct.is_(True), 1), else_=0)), 0)
_wrong = func.coalesce(func.sum(case((ChallengeAttempt.is_correct.is_(True), 0), else_=1)), 0)


def active_workers(db: Session, company_id: int) -> list[User]:
    return list(db.scalars(
        select(User).options(selectinload(User.area))
        .where(User.company_id == company_id, User.role == "worker", User.is_active.is_(True))
        .order_by(User.name)
    ).all())


def count_published_modules(db: Session, company_id: int) -> int:
    return db.scalar(select(func.count(LearningModule.id)).where(
        LearningModule.company_id == company_id, LearningModule.status == "published")) or 0


def count_published_challenges(db: Session, company_id: int) -> int:
    return db.scalar(select(func.count(Challenge.id)).where(
        Challenge.company_id == company_id, Challenge.status == "published")) or 0


def completed_modules_by_user(db: Session, company_id: int, user_id: int | None = None) -> dict[int, int]:
    """Módulos publicados que cada usuario terminó (completed_at es la fuente de verdad)."""
    q = (select(ModuleProgress.user_id, func.count(ModuleProgress.id))
         .join(LearningModule, LearningModule.id == ModuleProgress.module_id)
         .where(LearningModule.company_id == company_id, LearningModule.status == "published",
                ModuleProgress.completed_at.is_not(None))
         .group_by(ModuleProgress.user_id))
    if user_id is not None:
        q = q.where(ModuleProgress.user_id == user_id)
    return {uid: n for uid, n in db.execute(q).all()}


def challenge_results_by_user(db: Session, company_id: int, user_id: int | None = None) -> dict[int, tuple[int, int]]:
    """{user_id: (respondidos, correctos)} solo sobre retos publicados."""
    q = (select(ChallengeAttempt.user_id, func.count(ChallengeAttempt.id), _correct)
         .join(Challenge, Challenge.id == ChallengeAttempt.challenge_id)
         .where(Challenge.company_id == company_id, Challenge.status == "published")
         .group_by(ChallengeAttempt.user_id))
    if user_id is not None:
        q = q.where(ChallengeAttempt.user_id == user_id)
    return {uid: (int(n), int(c)) for uid, n, c in db.execute(q).all()}


def module_completion(db: Session, company_id: int, created_by: int | None = None):
    """[(módulo, nº de trabajadores activos que lo terminaron)]."""
    q = (select(LearningModule, func.count(User.id))
         .outerjoin(ModuleProgress, and_(ModuleProgress.module_id == LearningModule.id,
                                         ModuleProgress.completed_at.is_not(None)))
         .outerjoin(User, and_(User.id == ModuleProgress.user_id, User.role == "worker",
                               User.is_active.is_(True)))
         .where(LearningModule.company_id == company_id)
         .group_by(LearningModule.id).order_by(LearningModule.updated_at.desc()))
    if created_by is not None:
        q = q.where(LearningModule.created_by == created_by)
    return db.execute(q).all()


def challenge_performance(db: Session, company_id: int, created_by: int | None = None):
    """[(reto, intentos, correctos)]."""
    q = (select(Challenge, func.count(ChallengeAttempt.id), _correct)
         .outerjoin(ChallengeAttempt, ChallengeAttempt.challenge_id == Challenge.id)
         .where(Challenge.company_id == company_id)
         .group_by(Challenge.id).order_by(Challenge.updated_at.desc()))
    if created_by is not None:
        q = q.where(Challenge.created_by == created_by)
    return db.execute(q).all()


def topic_errors(db: Session, company_id: int, created_by: int | None = None, user_id: int | None = None, limit: int = 5):
    """[(tema, intentos, errores)] ordenado por más errores; solo temas con al menos un error."""
    q = (select(Challenge.topic, func.count(ChallengeAttempt.id), _wrong)
         .join(Challenge, Challenge.id == ChallengeAttempt.challenge_id)
         .where(Challenge.company_id == company_id, Challenge.status == "published")
         .group_by(Challenge.topic).having(_wrong > 0)
         .order_by(_wrong.desc(), Challenge.topic).limit(limit))
    if created_by is not None:
        q = q.where(Challenge.created_by == created_by)
    if user_id is not None:
        q = q.where(ChallengeAttempt.user_id == user_id)
    return db.execute(q).all()


def get_attempt(db: Session, user_id: int, challenge_id: int) -> ChallengeAttempt | None:
    return db.scalar(select(ChallengeAttempt).where(
        ChallengeAttempt.user_id == user_id, ChallengeAttempt.challenge_id == challenge_id))


def next_pending_challenge(db: Session, user: User) -> Challenge | None:
    answered = select(ChallengeAttempt.challenge_id).where(ChallengeAttempt.user_id == user.id)
    return db.scalar(select(Challenge).where(
        Challenge.company_id == user.company_id, Challenge.status == "published",
        Challenge.id.not_in(answered)).order_by(Challenge.id).limit(1))
