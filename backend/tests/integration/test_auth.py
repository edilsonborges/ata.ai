import pytest


@pytest.mark.asyncio
async def test_login_ok(client):
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev",
        "password": "ksjao10so!",
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev",
        "password": "nope",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_bearer(client):
    login = (await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev", "password": "ksjao10so!",
    })).json()
    r = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {login['access_token']}"
    })
    assert r.status_code == 200
    assert r.json()["email"] == "admin@edilson.dev"
