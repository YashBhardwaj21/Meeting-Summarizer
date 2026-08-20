import asyncio
import time
import uuid
import pytest
from unittest.mock import patch

from app.models.enums import JobStatus, MeetingStatus
from app.models.job import ProcessingJob
from app.models.meeting import Meeting
from app.models.file import File
from app.models.chat import Chat
from app.workers.transcription import run_transcription_pipeline
from app.integrations.asr.base import ASRSegment, ASRProvider
from app.integrations.embeddings.base import EmbeddingProvider


class FastDummyASRProvider(ASRProvider):
    """Mocks ASR to return dummy segments very quickly to test internal overhead."""
    async def transcribe(self, audio_path: str) -> list[ASRSegment]:
        # Return 100 dummy segments to simulate a long meeting
        segments = []
        for i in range(100):
            segments.append(
                ASRSegment(start=float(i), end=float(i + 1), text=f"This is segment {i} of the long benchmark meeting.")
            )
        return segments


class FastDummyEmbeddingProvider(EmbeddingProvider):
    """Mocks embedding generation to test DB insert performance."""
    @property
    def dimensions(self) -> int:
        return 1536
        
    @property
    def model_name(self) -> str:
        return "benchmark-embedding-model"
        
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Simulate processing delay
        await asyncio.sleep(0.01)
        return [[0.1] * 1536 for _ in texts]


@pytest.mark.asyncio
async def test_pipeline_performance_benchmark(db, test_engine, tmp_path):
    """
    Benchmarks the internal overhead of the transcription pipeline.
    This tests FFmpeg processing, text chunking, and database bulk inserts
    using a 10-minute audio file, while mocking out external network calls.
    """
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("FFmpeg not installed in test environment")
        
    # 1. Setup Database fixtures
    chat = Chat(id=uuid.uuid4(), title="Benchmark Chat")
    db.add(chat)
    
    # Generate 10 minute dummy audio
    dummy_wav = tmp_path / "10_min_benchmark.wav"
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=600", 
        "-c:a", "pcm_s16le", "-ar", "16000", str(dummy_wav)
    ], check=True, capture_output=True)
    
    file_record = File(
        id=uuid.uuid4(),
        chat_id=chat.id,
        filename="10_min_benchmark.wav", 
        mime_type="audio/wav",
        media_type="audio", 
        storage_key=str(dummy_wav),
        size_bytes=dummy_wav.stat().st_size
    )
    db.add(file_record)
    
    meeting = Meeting(id=uuid.uuid4(), chat_id=chat.id, file_id=file_record.id, title="Benchmark Meeting")
    db.add(meeting)
    
    job = ProcessingJob(
        id=uuid.uuid4(), 
        meeting_id=meeting.id,
        file_id=file_record.id,
        status=JobStatus.QUEUED.value
    )
    db.add(job)
    await db.commit()

    # 2. Mock external dependencies
    with patch("app.workers.worker.storage_service.check_object_exists", return_value=True):
        with patch("app.services.storage_service.generate_presigned_download_url", return_value=str(dummy_wav)):
            with patch("app.workers.transcription.get_asr_provider", return_value=FastDummyASRProvider()):
                with patch("app.workers.transcription.get_embedding_provider", return_value=FastDummyEmbeddingProvider()):
                    
                    # 3. Benchmark the Pipeline
                    start_time = time.perf_counter()
                    
                    metrics = {}
                    await run_transcription_pipeline(db, job, meeting, file_record, metrics)
                    
                    end_time = time.perf_counter()
                    total_overhead = end_time - start_time
                    
    # 4. Assert Performance Requirements
    # A 10 minute audio file should be processed by our internal pipeline 
    # (FFmpeg splitting, chunking, pgvector DB insert) in well under 10 seconds.
    assert total_overhead < 10.0, f"Pipeline overhead too high: {total_overhead:.2f}s for 10 min audio"
    
    # Verify metrics were populated correctly
    assert "media_duration_seconds" in metrics
    assert metrics["media_duration_seconds"] >= 599.0
    assert "total_wall_clock_ms" in metrics
    assert metrics["embedding"]["chunks"] > 0
