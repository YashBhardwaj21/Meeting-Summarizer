import pytest
from httpx import AsyncClient
from app.models.enums import ChatStatus

pytestmark = pytest.mark.asyncio


async def test_create_chat(client: AsyncClient):
    response = await client.post("/api/v1/chats", json={"title": "Team Sync"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "Team Sync"
    assert data["status"] == ChatStatus.ACTIVE.value


async def test_get_chat(client: AsyncClient):
    # 1. Create chat
    create_resp = await client.post("/api/v1/chats", json={"title": "Q3 Planning"})
    chat_id = create_resp.json()["id"]

    # 2. Get chat
    get_resp = await client.get(f"/api/v1/chats/{chat_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == chat_id
    assert data["title"] == "Q3 Planning"


async def test_get_nonexistent_chat(client: AsyncClient):
    import uuid
    chat_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/chats/{chat_id}")
    assert response.status_code == 404


async def test_delete_chat(client: AsyncClient):
    # 1. Create chat
    create_resp = await client.post("/api/v1/chats", json={"title": "To be deleted"})
    chat_id = create_resp.json()["id"]

    # 2. Delete chat
    delete_resp = await client.delete(f"/api/v1/chats/{chat_id}")
    assert delete_resp.status_code == 202

    # 3. Get chat (should return 404 because status is now 'deleting')
    get_resp = await client.get(f"/api/v1/chats/{chat_id}")
    assert get_resp.status_code == 404
