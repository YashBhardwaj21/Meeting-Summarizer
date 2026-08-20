import pytest
from httpx import AsyncClient
import httpx
from app.models.enums import UploadStatus

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
async def test_integration_upload_to_minio_video_and_audio(client: AsyncClient):
    """
    Test real MinIO integration with both a video and an audio file.
    Does not use mocks.
    """
    # 1. Create chat
    chat_resp = await client.post("/api/v1/chats", json={"title": "Integration Chat"})
    assert chat_resp.status_code == 201
    chat_id = chat_resp.json()["id"]

    # -- TEST VIDEO UPLOAD --
    video_bytes = b"fake video bytes"
    
    # 2. Presign video
    presign_video_resp = await client.post(
        f"/api/v1/chats/{chat_id}/uploads/presign",
        json={
            "filename": "meeting.mp4",
            "content_type": "video/mp4",
            "size_bytes": len(video_bytes),
        }
    )
    assert presign_video_resp.status_code == 200
    video_data = presign_video_resp.json()
    video_file_id = video_data["file_id"]
    video_upload_url = video_data["upload_url"]

    # 3. Actual PUT to MinIO
    async with httpx.AsyncClient() as direct_client:
        upload_resp = await direct_client.put(
            video_upload_url,
            content=video_bytes,
            headers={"Content-Type": "video/mp4"}
        )
        assert upload_resp.status_code == 200

    # 4. Complete upload
    complete_video_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{video_file_id}/complete")
    assert complete_video_resp.status_code == 200
    assert complete_video_resp.json()["upload_status"] == UploadStatus.UPLOADED.value


    # -- TEST AUDIO UPLOAD --
    audio_bytes = b"fake audio bytes"
    
    # 2. Presign audio
    presign_audio_resp = await client.post(
        f"/api/v1/chats/{chat_id}/uploads/presign",
        json={
            "filename": "meeting.mp3",
            "content_type": "audio/mpeg",
            "size_bytes": len(audio_bytes),
        }
    )
    assert presign_audio_resp.status_code == 200
    audio_data = presign_audio_resp.json()
    audio_file_id = audio_data["file_id"]
    audio_upload_url = audio_data["upload_url"]

    # 3. Actual PUT to MinIO
    async with httpx.AsyncClient() as direct_client:
        upload_resp = await direct_client.put(
            audio_upload_url,
            content=audio_bytes,
            headers={"Content-Type": "audio/mpeg"}
        )
        assert upload_resp.status_code == 200

    # 4. Complete upload
    complete_audio_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{audio_file_id}/complete")
    assert complete_audio_resp.status_code == 200
    assert complete_audio_resp.json()["upload_status"] == UploadStatus.UPLOADED.value


@pytest.mark.integration
async def test_integration_size_mismatch(client: AsyncClient):
    """
    Test size verification with real storage: upload smaller file than requested.
    """
    chat_resp = await client.post("/api/v1/chats", json={"title": "Integration Chat 2"})
    chat_id = chat_resp.json()["id"]

    expected_size = 1000
    actual_bytes = b"this is much less than 1000 bytes"
    
    presign_resp = await client.post(
        f"/api/v1/chats/{chat_id}/uploads/presign",
        json={
            "filename": "meeting.mp4",
            "content_type": "video/mp4",
            "size_bytes": expected_size,
        }
    )
    assert presign_resp.status_code == 200
    data = presign_resp.json()
    file_id = data["file_id"]
    upload_url = data["upload_url"]

    async with httpx.AsyncClient() as direct_client:
        upload_resp = await direct_client.put(
            upload_url,
            content=actual_bytes,
            headers={"Content-Type": "video/mp4"}
        )
        assert upload_resp.status_code == 200

    complete_resp = await client.post(f"/api/v1/chats/{chat_id}/files/{file_id}/complete")
    assert complete_resp.status_code == 400
    assert complete_resp.json()["error"]["code"] == "UPLOADED_SIZE_MISMATCH"
