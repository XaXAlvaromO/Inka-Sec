from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from conftest import API


def test_hello():
    res = TestClient(app).get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_checks_the_database(Session):
    res = TestClient(app).get(f"{API}/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "database": "connected"}


def test_health_reports_503_when_database_is_down():
    # Ruta imposible: SQLite no puede abrir el archivo, igual que un Postgres caído.
    broken = sessionmaker(bind=create_engine("sqlite:////ruta/que/no/existe/inkasec.db"))

    def broken_db():
        session = broken()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = broken_db
    try:
        res = TestClient(app).get(f"{API}/health")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 503
    assert "Traceback" not in res.text  # no se filtran detalles internos
