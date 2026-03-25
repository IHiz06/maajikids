"""
Tests: Autenticación
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_register_success(client):
    r = client.post("/autenticacion/registrar", json={
        "email": "test_parent@test.com",
        "password": "Test1234!",
        "first_name": "Maria",
        "last_name": "Lopez",
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["success"] is True


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@test.com",
        "password": "Test1234!",
        "first_name": "A",
        "last_name": "B",
    }
    client.post("/autenticacion/registrar", json=payload)
    r = client.post("/autenticacion/registrar", json=payload)
    assert r.status_code == 409


def test_login_unverified(client):
    client.post("/autenticacion/registrar", json={
        "email": "unverified@test.com",
        "password": "Test1234!",
        "first_name": "X",
        "last_name": "Y",
    })
    r = client.post("/autenticacion/iniciar-sesion", json={
        "email": "unverified@test.com",
        "password": "Test1234!",
    })
    assert r.status_code == 403


def test_admin_login(client):
    r = client.post("/autenticacion/iniciar-sesion", json={
        "email": "admin@maajikids.com",
        "password": "Admin123!",
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data["data"]
    assert data["data"]["user"]["role"]["name"] == "admin"


def test_protected_endpoint_without_token(client):
    r = client.get("/usuarios/")
    assert r.status_code == 401


def test_get_current_user(client, auth_headers):
    r = client.get("/usuarios/yo", headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()["data"]["email"] == "admin@maajikids.com"


def test_list_roles(client, auth_headers):
    r = client.get("/roles/", headers=auth_headers)
    assert r.status_code == 200
    roles = r.get_json()["data"]
    role_names = [role["name"] for role in roles]
    assert "admin" in role_names
    assert "parent" in role_names


def test_list_workshops_public(client):
    """Talleres son públicos, no requieren JWT."""
    r = client.get("/talleres/")
    assert r.status_code == 200


def test_create_workshop_requires_admin(client, auth_headers):
    r = client.post("/talleres/", json={
        "title": "Taller Test",
        "description": "Descripción de prueba",
        "schedule": "LUNES 10AM",
        "age_min": 6,
        "age_max": 24,
        "max_capacity": 10,
        "price": 50.0,
    }, headers=auth_headers)
    assert r.status_code == 201


def test_contact_public(client):
    r = client.post("/contacto/", json={
        "sender_name": "Juan Pérez",
        "sender_email": "juan@test.com",
        "subject": "Consulta sobre talleres",
        "body": "Quisiera saber más información sobre los talleres.",
    })
    assert r.status_code == 201


def test_chat_maaji_public(client):
    """El chat de Maaji es público."""
    r = client.post("/ia/chat", json={
        "mensaje": "¿Qué talleres tienen disponibles?",
    })
    # Puede fallar si no hay GEMINI_API_KEY configurada en tests
    assert r.status_code in (200, 502)
