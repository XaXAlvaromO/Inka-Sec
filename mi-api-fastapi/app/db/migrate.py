"""Columnas nuevas en tablas que ya existen.

create_all() crea las tablas que faltan, pero no agrega columnas a una tabla existente.
Este paso las agrega para que una base ya poblada (por ejemplo, la de Render) no tenga
que borrarse al actualizar. Solo agrega columnas opcionales o con valor por defecto;
nunca borra ni cambia datos.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.models.challenge import Challenge, ChallengeAttempt

# (modelo, columna). La definición sale del propio modelo, así no hay dos fuentes de verdad.
NEW_COLUMNS = [
    (Challenge, "kind"),
    (Challenge, "content"),
    (ChallengeAttempt, "tries"),
    (ChallengeAttempt, "last_correct"),
    (ChallengeAttempt, "last_score"),
]


def _ddl(engine: Engine, model, name: str) -> str:
    column = model.__table__.c[name]
    preparer = engine.dialect.identifier_preparer
    ddl = f"ALTER TABLE {preparer.quote(model.__tablename__)} ADD COLUMN {preparer.quote(name)} {column.type.compile(dialect=engine.dialect)}"
    if column.server_default is not None:
        value = column.server_default.arg
        ddl += f" DEFAULT '{value}'" if column.type.python_type is str else f" DEFAULT {value}"
    return ddl


def ensure_columns(engine: Engine) -> list[str]:
    """Agrega las columnas que falten. Devuelve las que agregó (tabla.columna)."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    added = []
    with engine.begin() as conn:
        for model, name in NEW_COLUMNS:
            table = model.__tablename__
            if table not in tables:
                continue  # create_all la crea completa
            existing = {c["name"] for c in inspector.get_columns(table)}
            if name in existing:
                continue
            # Nombres fijos sacados del modelo (NEW_COLUMNS), nunca entrada del usuario.
            conn.execute(text(_ddl(engine, model, name)))  # nosec B608
            added.append(f"{table}.{name}")
    return added
