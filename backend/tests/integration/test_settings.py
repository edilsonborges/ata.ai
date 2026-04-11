import pytest


async def _token(client) -> str:
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev", "password": "ksjao10so!",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_list_providers_seeded(client):
    t = await _token(client)
    r = await client.get("/api/settings/providers", headers={"Authorization": f"Bearer {t}"})
    assert r.status_code == 200
    providers = {p["provider"] for p in r.json()}
    assert providers == {"anthropic", "openai", "openrouter", "claude_cli"}


@pytest.mark.asyncio
async def test_upsert_anthropic_api_key(client):
    t = await _token(client)
    r = await client.put(
        "/api/settings/providers/anthropic",
        headers={"Authorization": f"Bearer {t}"},
        json={"api_key": "sk-ant-test", "default_model": "claude-opus-4-6", "enabled": True},
    )
    assert r.status_code == 200
    assert r.json()["has_api_key"] is True
    assert r.json()["enabled"] is True
