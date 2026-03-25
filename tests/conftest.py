"""
MaajiKids — Configuración de pruebas pytest
"""
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Crea la app en modo testing con SQLite en memoria."""
    app = create_app("testing")
    ctx = app.app_context()
    ctx.push()
    _db.create_all()
    yield app
    _db.drop_all()
    ctx.pop()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def clean_db(app):
    """Limpia la BD entre tests."""
    yield
    _db.session.rollback()


@pytest.fixture
def admin_token(client):
    """Retorna un access_token de admin para usar en tests."""
    resp = client.post("/autenticacion/iniciar-sesion", json={
        "email": "admin@maajikids.com",
        "password": "Admin123!",
    })
    data = resp.get_json()
    return data.get("data", {}).get("access_token", "")


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
