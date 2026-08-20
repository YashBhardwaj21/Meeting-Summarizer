"""Tests for the media service using real FFmpeg binaries."""

import pytest
import shutil
import subprocess
from pathlib import Path

from app.services.media_service import inspect_media, extract_audio, split_audio
from app.exceptions import PermanentProcessingError

# Helper to check if ffmpeg is available on the host running tests
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.fixture
def dummy_audio(tmp_path) -> str:
    """Create a short 5-second 440Hz sine wave WAV file using FFmpeg."""
    if not HAS_FFMPEG:
        pytest.skip("FFmpeg not installed")
        
    output_path = tmp_path / "dummy.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        str(output_path)
    ], check=True, capture_output=True)
    
    return str(output_path)


@pytest.mark.asyncio
async def test_inspect_media(dummy_audio):
    """Test inspecting a real media file."""
    metadata = await inspect_media(dummy_audio)
    assert metadata.has_audio is True
    assert metadata.has_video is False
    assert 4.9 <= metadata.duration_seconds <= 5.1


@pytest.mark.asyncio
async def test_inspect_media_missing():
    """Test inspecting a missing file raises PermanentProcessingError."""
    with pytest.raises(PermanentProcessingError) as exc:
        await inspect_media("/tmp/does_not_exist_ever.wav")
    assert exc.value.error_code == "MEDIA_NOT_FOUND"


@pytest.mark.asyncio
async def test_extract_audio(dummy_audio, tmp_path):
    """Test extracting audio to FLAC format."""
    output_flac = str(tmp_path / "output.flac")
    result = await extract_audio(dummy_audio, output_flac)
    
    assert result == output_flac
    assert Path(output_flac).exists()
    
    # Inspect the output to ensure it's 16kHz mono FLAC
    metadata = await inspect_media(output_flac)
    assert metadata.format_name == "flac"
    assert metadata.has_audio is True


@pytest.mark.asyncio
async def test_split_audio(dummy_audio):
    """Test splitting audio into chunks with overlap."""
    # Split 5-second audio into 3-second chunks with 1-second overlap
    chunks = await split_audio(dummy_audio, chunk_duration=3, overlap=1)
    
    # Chunk 1: 0 to 3s
    # Chunk 2: 2 to 5s
    assert len(chunks) == 2
    
    assert chunks[0].offset_seconds == 0.0
    assert 2.9 <= chunks[0].duration_seconds <= 3.1
    
    assert chunks[1].offset_seconds == 2.0
    assert 2.9 <= chunks[1].duration_seconds <= 3.1
