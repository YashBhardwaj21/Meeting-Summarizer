import asyncio
import logging
import time
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError
from app.models.enums import JobStatus
from app.models.job import ProcessingJob
from app.models.meeting import Meeting
from app.models.file import File
from app.services import job_service
from app.services.media_service import inspect_media, extract_audio
from app.integrations.asr import get_asr_provider
from app.services.transcription_service import transcribe_audio, align_speakers
from app.integrations.diarization import get_diarization_provider
from app.services.transcript_service import replace_meeting_transcript, replace_meeting_chunks
from app.services.token_counter import TiktokenCounter
from app.services.chunking_service import create_semantic_chunks
from app.integrations.embeddings import get_embedding_provider
from app.services.embedding_service import embed_chunks

logger = logging.getLogger(__name__)


async def _check_cancelled(db: AsyncSession, job_id: UUID) -> bool:
    """Check if the job has been cancelled."""
    job = await job_service.get_job(db, job_id)
    return job.status == JobStatus.CANCELLED.value


def _cleanup_temp_dir(job_id: UUID) -> None:
    """Clean up temporary files for a job."""
    settings = get_settings()
    temp_dir = Path(settings.media_temp_dir) / str(job_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


async def run_transcription_pipeline(
    db: AsyncSession, 
    job: ProcessingJob, 
    meeting: Meeting, 
    file_record: File, 
    metrics: dict
) -> None:
    """
    Run the full transcription pipeline.
    This replaces the placeholder `asyncio.sleep()` stages with real processing.
    """
    settings = get_settings()
    job_id = job.id
    metrics["pipeline_version"] = settings.processing_pipeline_version
    total_start_time = time.monotonic()
    
    # Ensure temp dir exists
    temp_dir = Path(settings.media_temp_dir) / str(job_id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download file to local storage
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="downloading")
        await db.commit()
        
        from app.services import storage_service
        local_input_path = str(temp_dir / f"input{Path(file_record.filename).suffix}")
        
        await asyncio.to_thread(storage_service.download_object, file_record.storage_key, local_input_path)
        
        # Validate download
        local_path_obj = Path(local_input_path)
        if not local_path_obj.exists():
            raise PermanentProcessingError("Downloaded file is missing.", error_code="DOWNLOAD_FAILED")
        if local_path_obj.stat().st_size != file_record.size_bytes:
            raise PermanentProcessingError(f"Downloaded file size mismatch. Expected {file_record.size_bytes}, got {local_path_obj.stat().st_size}.", error_code="DOWNLOAD_CORRUPT")
        
        # 1. Media Inspection
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="media_inspection")
        await db.commit()
        
        logger.info("[PIPELINE] Starting media inspection")
        t0 = time.monotonic()
        media_metadata = await inspect_media(local_input_path)
        metrics["media_inspection_time_ms"] = int((time.monotonic() - t0) * 1000)
        metrics["media_duration_seconds"] = media_metadata.duration_seconds
        metrics["media_size_bytes"] = media_metadata.size_bytes
        
        # 2. Audio Extraction
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="audio_extraction")
        await db.commit()
        
        logger.info("[PIPELINE] Starting audio extraction")
        t1 = time.monotonic()
        flac_path = str(temp_dir / "normalized.flac")
        await extract_audio(local_input_path, flac_path, metadata=media_metadata)
        metrics["audio_extraction_time_ms"] = int((time.monotonic() - t1) * 1000)
        
        # 3. Transcription
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="transcription")
        await db.commit()
        
        logger.info("[PIPELINE] Starting transcription")
        t2 = time.monotonic()
        asr_provider = get_asr_provider()
        
        metrics["asr"] = {
            "provider": settings.asr_provider,
            "model": settings.asr_model,
            "concurrency": settings.asr_concurrency,
        }
        
        canonical_segments = await transcribe_audio(
            audio_path=flac_path,
            provider=asr_provider,
            chunk_duration=settings.asr_chunk_duration_seconds,
            overlap=settings.asr_chunk_overlap_seconds,
            concurrency=settings.asr_concurrency,
            metadata=media_metadata
        )
        metrics["asr_wall_time_ms"] = int((time.monotonic() - t2) * 1000)
        logger.info(f"[PIPELINE] Finished transcription in {metrics['asr_wall_time_ms']/1000}s")
        
        # 3.5. Persist Transcript (EARLY CHECKPOINT)
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="persist_transcript_early")
        await db.commit()
        
        t3 = time.monotonic()
        db_segments = await replace_meeting_transcript(db, meeting.id, canonical_segments)
        
        from app.models.enums import MeetingStatus
        meeting.status = MeetingStatus.TRANSCRIPT_READY.value
        await db.commit()
        
        # 4. Diarization
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="diarization")
        await db.commit()
        
        logger.info("[PIPELINE] Starting diarization")
        t_diarization = time.monotonic()
        diarization_provider = get_diarization_provider()
        if diarization_provider:
            diarization_segments = await diarization_provider.diarize(flac_path)
            canonical_segments = align_speakers(
                canonical_segments,
                diarization_segments
            )
        metrics["diarization_wall_time_ms"] = int((time.monotonic() - t_diarization) * 1000)
        metrics["diarization"] = {
            "provider": settings.diarization_model,
        }
        logger.info(f"[PIPELINE] Finished diarization in {metrics['diarization_wall_time_ms']/1000}s")
            
        # 5. Persist Transcript (UPDATE SPEAKERS)
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="persist_transcript_speakers")
        await db.commit()
        
        db_segments = await replace_meeting_transcript(db, meeting.id, canonical_segments)
        # We need the UUIDs assigned by the database for the next step
        segment_uuids = [seg.id for seg in db_segments]
        metrics["transcript_persist_time_ms"] = int((time.monotonic() - t3) * 1000)
        await db.commit()
        
        # 6. Semantic Chunking
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="chunking")
        await db.commit()
        
        t4 = time.monotonic()
        token_counter = TiktokenCounter(settings.tokenizer_encoding)
        chunks = create_semantic_chunks(
            segments=canonical_segments,
            segment_uuids=segment_uuids,
            max_tokens=settings.transcript_chunk_max_tokens,
            overlap_tokens=settings.transcript_chunk_overlap_tokens,
            token_counter=token_counter
        )
        metrics["chunking_time_ms"] = int((time.monotonic() - t4) * 1000)
        
        # 7. Embedding
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="embedding")
        await db.commit()
        
        logger.info("[PIPELINE] Starting embedding")
        t5 = time.monotonic()
        embedding_provider = get_embedding_provider()
        
        metrics["embedding"] = {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "chunks": len(chunks)
        }
        
        embeddings = await embed_chunks(
            chunks=chunks,
            provider=embedding_provider,
            batch_size=settings.embedding_batch_size
        )
        metrics["embedding_wall_time_ms"] = int((time.monotonic() - t5) * 1000)
        logger.info(f"[PIPELINE] Finished embedding in {metrics['embedding_wall_time_ms']/1000}s")
        
        # 8. Persist Index (DURABLE CHECKPOINT)
        if await _check_cancelled(db, job_id): raise asyncio.CancelledError()
        await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="persist_index")
        await db.commit()
        
        t6 = time.monotonic()
        await replace_meeting_chunks(
            db=db,
            meeting_id=meeting.id,
            chat_id=meeting.chat_id,
            chunks=chunks,
            embeddings=embeddings,
            model_name=embedding_provider.model_name,
            dimensions=embedding_provider.dimensions
        )
        metrics["indexing_time_ms"] = int((time.monotonic() - t6) * 1000)
        metrics["total_wall_clock_ms"] = int((time.monotonic() - total_start_time) * 1000)
        
    finally:
        _cleanup_temp_dir(job_id)
