import pytest
from app.services.transcription_service import _merge_and_deduplicate, CanonicalSegment

def test_dedup_no_overlap():
    """Segments that do not overlap in time are both kept."""
    chunk1 = [
        CanonicalSegment(0.0, 2.0, "Hello world"),
    ]
    chunk2 = [
        CanonicalSegment(2.1, 4.0, "This is a test"),
    ]
    
    result = _merge_and_deduplicate([chunk1, chunk2], overlap=1.0, chunk_duration=3.0)
    
    assert len(result) == 2
    assert result[0].text == "Hello world"
    assert result[1].text == "This is a test"


def test_dedup_exact_match():
    """Segments that overlap in time AND text are deduplicated."""
    chunk1 = [
        CanonicalSegment(0.0, 2.0, "Hello world"),
        CanonicalSegment(2.0, 3.0, "It is a beautiful day"),  # In overlap window
    ]
    chunk2 = [
        CanonicalSegment(2.0, 3.0, "It is a beautiful day"),  # Duplicate
        CanonicalSegment(3.0, 5.0, "Let's go outside"),
    ]
    
    result = _merge_and_deduplicate([chunk1, chunk2], overlap=1.0, chunk_duration=3.0)
    
    assert len(result) == 3
    assert result[0].text == "Hello world"
    assert result[1].text == "It is a beautiful day"
    assert result[2].text == "Let's go outside"


def test_dedup_different_text_same_time():
    """Segments that overlap in time but have different text are NOT deduplicated (cross-talk)."""
    chunk1 = [
        CanonicalSegment(0.0, 2.0, "Hello world"),
        CanonicalSegment(2.0, 3.0, "Speaker A saying something"),  # In overlap
    ]
    chunk2 = [
        CanonicalSegment(2.1, 3.0, "Speaker B interrupting"),      # In overlap
        CanonicalSegment(3.0, 5.0, "Let's go outside"),
    ]
    
    result = _merge_and_deduplicate([chunk1, chunk2], overlap=1.0, chunk_duration=3.0)
    
    assert len(result) == 4
    assert result[0].text == "Hello world"
    assert result[1].text == "Speaker A saying something"
    assert result[2].text == "Speaker B interrupting"
    assert result[3].text == "Let's go outside"


def test_dedup_fuzzy_match():
    """Segments that overlap in time and have fuzzy matching text are deduplicated."""
    chunk1 = [
        CanonicalSegment(2.0, 3.0, "This is almost exactly the same"),
    ]
    chunk2 = [
        CanonicalSegment(2.1, 3.1, "This is almost exact the same"),
    ]
    
    result = _merge_and_deduplicate([chunk1, chunk2], overlap=1.0, chunk_duration=3.0)
    
    assert len(result) == 1
    # We expect it to keep the first one
    assert result[0].text == "This is almost exactly the same"


def test_dedup_longer_duplicate_updates_text():
    """If the second duplicate has more content, it updates the first."""
    chunk1 = [
        CanonicalSegment(2.0, 3.0, "I think we should"),
    ]
    chunk2 = [
        CanonicalSegment(2.0, 4.0, "I think we should go to the store"),
    ]
    
    result = _merge_and_deduplicate([chunk1, chunk2], overlap=2.0, chunk_duration=3.0)
    
    assert len(result) == 1
    assert result[0].text == "I think we should go to the store"
    assert result[0].end_time == 4.0
