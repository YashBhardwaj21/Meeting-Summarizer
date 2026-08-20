import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.models.enums import UploadStatus

pytestmark = pytest.mark.asyncio


async def test_request_presign_success(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="https://mock-url.com/upload"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={
                "filename": "meeting.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024 * 1024 * 10,  # 10 MB
            }
        )
        
    assert presign_resp.status_code == 200
    data = presign_resp.json()
    assert "file_id" in data
    assert data["upload_url"] == "https://mock-url.com/upload"


async def test_request_presign_invalid_extension(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    presign_resp = await client.post(
        f"/api/v1/chats/{chat_id}/uploads/presign",
        json={
            "filename": "meeting.exe",
            "content_type": "application/x-msdownload",
            "size_bytes": 1024,
        }
    )
        
    assert presign_resp.status_code == 400
    assert presign_resp.json()["error"]["code"] == "UNSUPPORTED_EXTENSION"


async def test_complete_upload_success(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="url"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={
                "filename": "meeting.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024,
            }
        )
    file_id = presign_resp.json()["file_id"]
    
    # Complete upload
    with patch("app.services.storage_service.get_object_metadata", return_value={"ContentLength": 1024}):
        complete_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
        
    assert complete_resp.status_code == 200
    assert complete_resp.json()["upload_status"] == UploadStatus.UPLOADED.value


async def test_complete_upload_object_not_found(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="url"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={
                "filename": "meeting.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024,
            }
        )
    file_id = presign_resp.json()["file_id"]
    
    # Complete upload but object doesn't exist
    with patch("app.services.storage_service.get_object_metadata", return_value=None):
        complete_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
        
    assert complete_resp.status_code == 400
    assert complete_resp.json()["error"]["code"] == "OBJECT_NOT_FOUND"


async def test_complete_upload_size_mismatch(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="url"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={
                "filename": "meeting.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024,
            }
        )
    file_id = presign_resp.json()["file_id"]
    
    # Complete upload but size doesn't match
    with patch("app.services.storage_service.get_object_metadata", return_value={"ContentLength": 9999}):
        complete_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
        
    assert complete_resp.status_code == 400
    assert complete_resp.json()["error"]["code"] == "UPLOADED_SIZE_MISMATCH"


async def test_complete_upload_idempotency(client: AsyncClient):
    # Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # Request presign
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="url"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={
                "filename": "meeting.mp4",
                "content_type": "video/mp4",
                "size_bytes": 1024,
            }
        )
    file_id = presign_resp.json()["file_id"]
    
    # Complete upload first time
    with patch("app.services.storage_service.get_object_metadata", return_value={"ContentLength": 1024}):
        resp1 = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
        assert resp1.status_code == 200
        
        # Complete upload second time (should be idempotent)
        resp2 = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
        assert resp2.status_code == 200
