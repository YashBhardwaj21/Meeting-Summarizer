import asyncio
import uuid
import pytest
from sqlalchemy import select
from unittest.mock import patch, AsyncMock

from app.models.enums import JobStatus, MeetingStatus
from app.models.job import ProcessingJob
from app.models.meeting import Meeting
from app.models.file import File
from app.models.chat import Chat
from app.models.transcript import TranscriptSegment
from app.models.transcript_chunk import TranscriptChunk
from app.workers.worker import process_meeting_job
from app.integrations.asr.base import ASRSegment, ASRProvider
from app.integrations.embeddings.base import EmbeddingProvider


class DummyASRProvider(ASRProvider):
    async def transcribe(self, audio_path: str) -> list[ASRSegment]:
        # Return some dummy segments
        return [
            ASRSegment(start=0.0, end=3.0, text="Hello world from dummy ASR."),
            ASRSegment(start=3.0, end=5.0, text="This is a test of the processing pipeline.")
        ]


class DummyEmbeddingProvider(EmbeddingProvider):
    @property
    def dimensions(self) -> int:
        return 1536
        
    @property
    def model_name(self) -> str:
        return "dummy-embedding-model"
        
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Return a dummy vector of length 1536 for each text
        return [[0.1] * 1536 for _ in texts]


@pytest.mark.asyncio
async def test_full_processing_pipeline(db, tmp_path):
    """
    Test the full worker pipeline end-to-end, mocking out the external API providers.
    Requires FFmpeg to be available in the test environment (checked automatically).
    """
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("FFmpeg not installed in test environment")
        
    # 1. Setup Database fixtures
    chat = Chat(id=uuid.uuid4(), title="Test Chat")
    db.add(chat)
    
    # We create a dummy audio file directly on disk to mock the storage service
    dummy_wav = tmp_path / "dummy.wav"
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=5", 
        "-c:a", "pcm_s16le", "-ar", "16000", str(dummy_wav)
    ], check=True, capture_output=True)
    
    file_record = File(
        id=uuid.uuid4(),
        chat_id=chat.id,
        filename="dummy.wav", 
        mime_type="audio/wav",
        media_type="audio", 
        storage_key=str(dummy_wav),  # Hack: point storage_key directly to local path
        size_bytes=dummy_wav.stat().st_size
    )
    db.add(file_record)
    
    meeting = Meeting(id=uuid.uuid4(), chat_id=chat.id, file_id=file_record.id, title="Test Meeting")
    db.add(meeting)
    
    job = ProcessingJob(
        id=uuid.uuid4(), 
        meeting_id=meeting.id,
        file_id=file_record.id,
        status=JobStatus.QUEUED.value
    )
    db.add(job)
    await db.commit()

    from tests.conftest import TestingSessionLocal
    
    # 2. Mock external dependencies
    with patch("app.workers.worker.storage_service.check_object_exists", return_value=True):
        with patch("app.services.storage_service.generate_presigned_download_url", return_value=str(dummy_wav)):
            with patch("app.workers.transcription.get_asr_provider", return_value=DummyASRProvider()):
                with patch("app.workers.transcription.get_embedding_provider", return_value=DummyEmbeddingProvider()):
                    with patch("app.workers.worker.async_session_factory", side_effect=TestingSessionLocal):
                        
                        # 3. Execute Worker Job
                        ctx = {"job_try": 1}
                        await process_meeting_job(ctx, str(job.id))
                    
    # 4. Assert Results
    await db.refresh(job)
    await db.refresh(meeting)
    
    assert job.status == JobStatus.COMPLETED.value
    assert job.stage == "complete"
    assert meeting.status == MeetingStatus.READY.value
    
    assert job.processing_metrics is not None
    assert "media_duration_seconds" in job.processing_metrics
    assert job.processing_metrics["media_duration_seconds"] >= 4.9 # approx 5s
    
    # Verify Transcripts were saved
    result = await db.execute(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id))
    segments = list(result.scalars().all())
    assert len(segments) > 0
    assert segments[0].text == "Hello world from dummy ASR."
    
    # Verify Chunks were saved with embeddings
    result = await db.execute(select(TranscriptChunk).where(TranscriptChunk.meeting_id == meeting.id))
    chunks = list(result.scalars().all())
    assert len(chunks) > 0
    assert chunks[0].embedding_dimensions == 1536
    # pgvector returns the array as a list/ndarray
    assert len(chunks[0].embedding) == 1536
