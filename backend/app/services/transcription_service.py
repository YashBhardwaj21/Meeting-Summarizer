import asyncio
import logging
from dataclasses import dataclass
from fuzzywuzzy import fuzz

from app.integrations.asr.base import ASRProvider, ASRSegment
from app.services.media_service import split_audio, AudioChunk

logger = logging.getLogger(__name__)


@dataclass
class CanonicalSegment:
    """A segment with globally corrected timestamps and no duplication."""
    start_time: float
    end_time: float
    text: str
    speaker: str | None = None


def _normalize_text(text: str) -> str:
    """Normalize text for similarity comparison."""
    # Lowercase and remove basic punctuation spaces
    return text.lower().strip()


def _is_similar(text1: str, text2: str, threshold: int = 85) -> bool:
    """Check if two segments have similar text using fuzzy matching."""
    norm1 = _normalize_text(text1)
    norm2 = _normalize_text(text2)
    
    # Fast paths
    if norm1 == norm2:
        return True
    if norm1 in norm2 or norm2 in norm1:
        return True
        
    return fuzz.ratio(norm1, norm2) >= threshold


async def transcribe_audio(
    audio_path: str,
    provider: ASRProvider,
    chunk_duration: int,
    overlap: int,
    concurrency: int,
) -> list[CanonicalSegment]:
    """
    1. Split audio into overlapping chunks
    2. Transcribe in parallel (bounded by concurrency)
    3. Correct global timestamps
    4. Deduplicate overlap regions
    """
    
    chunks = await split_audio(audio_path, chunk_duration, overlap)
    
    # Process chunks in parallel with a semaphore
    semaphore = asyncio.Semaphore(concurrency)
    
    async def process_chunk(chunk: AudioChunk, index: int) -> tuple[int, list[CanonicalSegment]]:
        async with semaphore:
            asr_segments = await provider.transcribe(chunk.path)
            
            # Correct timestamps
            canonical = []
            for seg in asr_segments:
                canonical.append(CanonicalSegment(
                    start_time=chunk.offset_seconds + seg.start,
                    end_time=chunk.offset_seconds + seg.end,
                    text=seg.text,
                    speaker=None
                ))
            return index, canonical

    # Execute all transcription tasks
    tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)
    
    # Sort results back into sequential order
    results.sort(key=lambda x: x[0])
    ordered_chunks = [segments for _, segments in results]
    
    if not ordered_chunks:
        return []

    return _merge_and_deduplicate(ordered_chunks, overlap, chunk_duration)


def _merge_and_deduplicate(
    ordered_chunks: list[list[CanonicalSegment]], 
    overlap: float,
    chunk_duration: float
) -> list[CanonicalSegment]:
    """
    Merge sequential chunks and deduplicate text in the overlap windows.
    Timestamp-aware FIRST, text-aware SECOND.
    """
    if len(ordered_chunks) == 1:
        return ordered_chunks[0]
        
    final_segments: list[CanonicalSegment] = []
    
    for i in range(len(ordered_chunks)):
        current_chunk = ordered_chunks[i]
        
        if i == 0:
            final_segments.extend(current_chunk)
            continue
            
        previous_chunk = ordered_chunks[i - 1]
        
        # Calculate where the overlap occurred globally
        # If chunks advance by (chunk_duration - overlap), the overlap starts at
        # the end of the previous chunk minus the overlap duration.
        # It's easier just to look at the current chunk's offset:
        # Assuming current_chunk's offset is X, the overlap is [X, X + overlap].
        
        # Find the earliest start time in the current chunk to estimate its offset
        if not current_chunk:
            continue
            
        current_offset = min(seg.start_time for seg in current_chunk)
        overlap_start = current_offset
        overlap_end = current_offset + overlap
        
        # Add non-overlapping segments from previous chunks normally
        # For the overlap region, we check for duplicates
        
        for curr_seg in current_chunk:
            # If the segment starts after the overlap window, no risk of duplicate
            if curr_seg.start_time >= overlap_end:
                final_segments.append(curr_seg)
                continue
                
            # It's in the overlap window. Check against recently added segments from the previous chunk
            # that also fall in the overlap window.
            is_duplicate = False
            
            # Look backwards in final_segments for overlapping candidates
            for prev_seg in reversed(final_segments):
                # Only check segments that end after the overlap window started
                if prev_seg.end_time < overlap_start:
                    break
                    
                # Time overlap check: do they overlap in time?
                time_overlap = max(0, min(curr_seg.end_time, prev_seg.end_time) - max(curr_seg.start_time, prev_seg.start_time))
                if time_overlap > 0:
                    # They overlap in time. Check text similarity.
                    if _is_similar(curr_seg.text, prev_seg.text):
                        # Duplicate found.
                        # Rule: keep the non-boundary occurrence.
                        # For prev_seg, it's near the END of its chunk (a boundary).
                        # For curr_seg, it's near the START of its chunk (a boundary).
                        # Actually, keeping the prev_seg is usually better because its start was deeper in the previous context,
                        # but Whisper sometimes hallucinates at boundaries. Let's keep the one that is LONGER, or just keep prev_seg.
                        # We'll just keep prev_seg to deduplicate.
                        is_duplicate = True
                        
                        # Optionally merge texts if curr_seg has more content
                        if len(curr_seg.text) > len(prev_seg.text) + 5:
                            prev_seg.text = curr_seg.text
                            prev_seg.end_time = max(prev_seg.end_time, curr_seg.end_time)
                            
                        break
                        
            if not is_duplicate:
                final_segments.append(curr_seg)
                
    # Finally, sort by start_time to ensure strict chronological order
    final_segments.sort(key=lambda s: s.start_time)
    
    return final_segments
