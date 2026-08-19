import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.models.enums import MeetingStatus, JobStatus

pytestmark = pytest.mark.asyncio


async def test_create_meeting(client: AsyncClient):
    # 1. Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Test Chat"})
    chat_id = chat_resp.json()["id"]

    # 2. Upload file
    with patch("app.services.storage_service.generate_presigned_upload_url", return_value="url"):
        presign_resp = await client.post(
            f"/api/v1/chats/{chat_id}/uploads/presign",
            json={"filename": "meeting.mp4", "content_type": "video/mp4", "size_bytes": 1024}
        )
    file_id = presign_resp.json()["file_id"]
    
    with patch("app.services.storage_service.check_object_exists", return_value=True):
        await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")

    # 3. Create meeting
    meeting_resp = await client.post(f"/api/v1/chats/{chat_id}/meetings", json={"file_id": file_id})
    assert meeting_resp.status_code == 201
    
    data = meeting_resp.json()
    assert "meeting" in data
    assert "job_id" in data
    assert data["job_status"] == JobStatus.QUEUED.value
    assert data["meeting"]["status"] == MeetingStatus.PENDING.value
    
    meeting_id = data["meeting"]["id"]
    job_id = data["job_id"]
    
    # 4. Check job status
    job_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == JobStatus.QUEUED.value
