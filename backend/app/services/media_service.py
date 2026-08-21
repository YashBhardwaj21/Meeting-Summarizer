"""Media processing service wrapping FFmpeg and ffprobe."""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError

logger = logging.getLogger(__name__)


@dataclass
class MediaMetadata:
    """Metadata extracted from media file using ffprobe."""
    duration_seconds: float
    size_bytes: int
    format_name: str
    has_audio: bool
    has_video: bool


@dataclass
class AudioChunk:
    """A segment of audio split from the main file."""
    path: str
    offset_seconds: float
    duration_seconds: float


async def _run_command(*args: str) -> tuple[str, str]:
    """Run a subprocess command and return stdout/stderr."""
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        logger.warning(f"Command cancelled, terminating subprocess: {' '.join(args)}")
        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"Command did not terminate, killing subprocess: {' '.join(args)}")
                process.kill()
                await process.wait()
        except Exception as e:
            logger.error(f"Failed to cleanup subprocess: {e}")
        raise
    
    if process.returncode != 0:
        cmd_str = " ".join(args)
        logger.error(f"Command failed: {cmd_str}\nStderr: {stderr.decode()}")
        raise PermanentProcessingError(
            f"Media processing command failed: {cmd_str}", 
            error_code="FFMPEG_FAILED"
        )
        
    return stdout.decode(), stderr.decode()


async def inspect_media(file_path: str) -> MediaMetadata:
    """Extract metadata from a media file using ffprobe."""
    if not Path(file_path).exists():
        raise PermanentProcessingError(f"File not found: {file_path}", error_code="MEDIA_NOT_FOUND")

    stdout, _ = await _run_command(
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    )
    
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise PermanentProcessingError("Invalid ffprobe output", error_code="MEDIA_INVALID") from e
        
    if "format" not in data:
        raise PermanentProcessingError("No format data found in media", error_code="MEDIA_INVALID")
        
    format_data = data["format"]
    streams = data.get("streams", [])
    
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    
    try:
        duration = float(format_data.get("duration", 0.0))
    except (ValueError, TypeError):
        duration = 0.0
        
    try:
        size = int(format_data.get("size", 0))
    except (ValueError, TypeError):
        size = 0
        
    # Validate duration against limits
    settings = get_settings()
    if duration > settings.max_media_duration_seconds:
        raise PermanentProcessingError(
            f"Media duration {duration}s exceeds maximum {settings.max_media_duration_seconds}s",
            error_code="MEDIA_INVALID"
        )

    return MediaMetadata(
        duration_seconds=duration,
        size_bytes=size,
        format_name=format_data.get("format_name", "unknown"),
        has_audio=has_audio,
        has_video=has_video
    )


async def extract_audio(input_path: str, output_path: str) -> str:
    """
    Extract first audio stream to 16kHz mono FLAC.
    Raises NO_AUDIO_TRACK if no audio is present.
    """
    metadata = await inspect_media(input_path)
    if not metadata.has_audio:
        raise PermanentProcessingError("File contains no audio tracks", error_code="NO_AUDIO_TRACK")
        
    # ffmpeg -i input -map 0:a:0 -ar 16000 -ac 1 -c:a flac output.flac
    await _run_command(
        "ffmpeg",
        "-y",               # Overwrite output files
        "-i", input_path,
        "-map", "0:a:0",    # First audio stream
        "-ar", "16000",     # 16 kHz sample rate (Whisper standard)
        "-ac", "1",         # Mono channel
        "-c:a", "flac",     # Lossless format
        output_path
    )
    
    if not Path(output_path).exists():
        raise PermanentProcessingError("Audio extraction failed to produce output", error_code="FFMPEG_FAILED")
        
    return output_path


async def split_audio(
    audio_path: str,
    chunk_duration: int,
    overlap: int,
) -> list[AudioChunk]:
    """
    Split normalized audio into overlapping chunks.
    This implementation uses FFmpeg's segment muxer. For exact overlaps,
    it might require complex filter graphs, but since the ASR stage deduplicates
    based on timestamps, we can just split sequentially without overlap at the audio level,
    OR use multiple FFmpeg passes for exact overlap if strictly required by ASR.
    
    Given ASR providers handle overlap poorly at boundaries without context,
    the standard way to get overlapping chunks via ffmpeg is a bit tricky, but here
    we will slice explicitly for each chunk, as it is robust for audio < 2 hours.
    """
    metadata = await inspect_media(audio_path)
    total_duration = metadata.duration_seconds
    
    if total_duration <= chunk_duration:
        return [AudioChunk(path=audio_path, offset_seconds=0.0, duration_seconds=total_duration)]
        
    chunks = []
    current_start = 0.0
    chunk_index = 0
    input_path = Path(audio_path)
    base_name = input_path.stem
    output_dir = input_path.parent
    
    while current_start < total_duration:
        # Calculate actual duration for this chunk (might be shorter at the end)
        actual_duration = min(chunk_duration, total_duration - current_start)
        if actual_duration <= 0:
            break
            
        chunk_file = str(output_dir / f"{base_name}_chunk{chunk_index:03d}.flac")
        
        # ffmpeg -y -ss START -i INPUT -t DURATION -c copy OUTPUT
        # Note: since input is already FLAC (intra-frame), stream copy (-c copy) 
        # might be tricky with exact timestamps. We will re-encode to FLAC to ensure
        # exact boundaries. It's fast enough.
        await _run_command(
            "ffmpeg",
            "-y",
            "-ss", str(current_start),
            "-i", audio_path,
            "-t", str(actual_duration),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "flac",
            chunk_file
        )
        
        # Verify the generated chunk
        if not Path(chunk_file).exists():
            raise PermanentProcessingError(f"Failed to generate chunk {chunk_index}", error_code="FFMPEG_FAILED")
            
        chunk_meta = await inspect_media(chunk_file)
        
        chunks.append(AudioChunk(
            path=chunk_file,
            offset_seconds=current_start,
            duration_seconds=chunk_meta.duration_seconds
        ))
        
        chunk_index += 1
        
        # If this chunk covered the end of the file, we are done
        if current_start + actual_duration >= total_duration:
            break
            
        # Advance by chunk_duration minus overlap
        current_start += (chunk_duration - overlap)
        
    return chunks
