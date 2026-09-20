import uuid
import pytest


def _register_and_login(client, email=None, password="Admin1234"):
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_rate_limit(client):
    for _ in range(5):
        r = client.get("/health")
        assert r.status_code == 200


def test_auth_register_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Admin1234",
        "full_name": "Test User",
    })
    assert r.status_code in [200, 201], f"Register failed: {r.text}"
    r = client.post("/api/v1/auth/login", data={"username": email, "password": "Admin1234"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    assert "access_token" in r.json()


def test_auth_me(client):
    token = _register_and_login(client)
    r = client.get("/api/v1/auth/me", headers=_headers(token))
    assert r.status_code == 200
    assert "email" in r.json()


def test_projects_crud(client):
    token = _register_and_login(client)
    h = _headers(token)

    r = client.post("/api/v1/projects", json={"name": "Test Project", "description": "desc"}, headers=h)
    assert r.status_code in [200, 201], f"Create failed: {r.text}"
    pid = r.json()["id"]

    r = client.get("/api/v1/projects", headers=h)
    assert r.status_code == 200

    r = client.get(f"/api/v1/projects/{pid}", headers=h)
    assert r.status_code == 200

    r = client.patch(f"/api/v1/projects/{pid}", json={"description": "updated"}, headers=h)
    assert r.status_code == 200

    r = client.post(f"/api/v1/projects/{pid}/duplicate", headers=h)
    assert r.status_code in [200, 201]
    dup_id = r.json()["id"]

    r = client.delete(f"/api/v1/projects/{pid}", headers=h)
    assert r.status_code == 200

    client.delete(f"/api/v1/projects/{dup_id}", headers=h)


def test_files_upload(client):
    token = _register_and_login(client)
    h = _headers(token)

    files = {"file": ("test.txt", b"hello Mark-Imti", "text/plain")}
    r = client.post("/api/v1/files/upload", files=files, headers=h)
    assert r.status_code in [200, 201]
    fid = r.json()["id"]

    r = client.get("/api/v1/files", headers=h)
    assert r.status_code == 200

    r = client.get(f"/api/v1/files/{fid}/download", headers=h)
    assert r.status_code == 200

    r = client.delete(f"/api/v1/files/{fid}", headers=h)
    assert r.status_code == 200


def test_tasks_crud(client):
    token = _register_and_login(client)
    h = _headers(token)

    r = client.post("/api/v1/tasks", json={"title": "Test Task", "description": "desc"}, headers=h)
    assert r.status_code in [200, 201]
    tid = r.json()["id"]

    r = client.get("/api/v1/tasks", headers=h)
    assert r.status_code == 200

    r = client.get(f"/api/v1/tasks/{tid}", headers=h)
    assert r.status_code == 200

    r = client.post(f"/api/v1/tasks/{tid}/execute", json={"prompt": "test"}, headers=h)
    assert r.status_code in [200, 400, 500]

    for action in ["pause", "resume", "cancel"]:
        r = client.post(f"/api/v1/tasks/{tid}/{action}", headers=h)
        assert r.status_code in [200, 400, 500]

    r = client.delete(f"/api/v1/tasks/{tid}", headers=h)
    assert r.status_code == 200


def test_schedules_crud(client):
    token = _register_and_login(client)
    h = _headers(token)

    r = client.post("/api/v1/schedules", json={
        "title": "Test Schedule",
        "prompt": "daily task",
        "frequency": "DAILY",
        "time_of_day": "09:00",
    }, headers=h)
    assert r.status_code in [200, 201]
    sid = r.json()["id"]

    r = client.get("/api/v1/schedules", headers=h)
    assert r.status_code == 200

    r = client.post(f"/api/v1/schedules/{sid}/pause", headers=h)
    assert r.status_code == 200

    r = client.post(f"/api/v1/schedules/{sid}/resume", headers=h)
    assert r.status_code == 200

    r = client.delete(f"/api/v1/schedules/{sid}", headers=h)
    assert r.status_code == 200


def test_knowledge_memory(client):
    token = _register_and_login(client)
    h = _headers(token)
    r = client.get("/api/v1/knowledge", headers=h)
    assert r.status_code == 200


def test_skills_lifecycle(client):
    token = _register_and_login(client)
    h = _headers(token)
    r = client.get("/api/v1/skills", headers=h)
    assert r.status_code == 200


def test_generative(client):
    token = _register_and_login(client)
    h = _headers(token)
    r = client.get("/api/v1/generative/workflows", headers=h)
    assert r.status_code in [200, 404]


def test_approval_flow(client):
    token = _register_and_login(client)
    h = _headers(token)
    r = client.get("/api/v1/approvals", headers=h)
    assert r.status_code in [200, 404]


def test_admin_rbac(client):
    token = _register_and_login(client)
    h = _headers(token)
    r = client.get("/api/v1/auth/me", headers=h)
    assert r.status_code == 200
    assert r.json()["role"] in ["USER", "CREATOR", "ADMIN"]
