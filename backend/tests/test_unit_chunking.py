import uuid
from app.services.chunking_service import create_semantic_chunks
from app.services.transcription_service import CanonicalSegment

class DummyCounter:
    def count(self, text: str) -> int:
        # 1 word = 1 token roughly for this test
        return len(text.split())


def test_chunking_token_limit():
    counter = DummyCounter()
    
    # 5 segments, each 10 words. Max tokens = 25.
    segments = [
        CanonicalSegment(0.0, 1.0, "word " * 10),
        CanonicalSegment(1.0, 2.0, "word " * 10),
        CanonicalSegment(2.0, 3.0, "word " * 10),
        CanonicalSegment(3.0, 4.0, "word " * 10),
        CanonicalSegment(4.0, 5.0, "word " * 10),
    ]
    uuids = [uuid.uuid4() for _ in segments]
    
    # Expect: 
    # Chunk 1: Seg 1 (10) + Seg 2 (10) = 20. Seg 3 would make 30 > 25. 
    # Chunk 2: Seg 3 (10) + Seg 4 (10) = 20.
    # Chunk 3: Seg 5 (10)
    # (Ignoring overlap for this specific basic flow)
    
    chunks = create_semantic_chunks(segments, uuids, max_tokens=25, overlap_tokens=0, token_counter=counter)
    
    assert len(chunks) == 3
    assert chunks[0].token_count == 20
    assert len(chunks[0].segment_ids) == 2
    
    assert chunks[1].token_count == 20
    assert len(chunks[1].segment_ids) == 2
    
    assert chunks[2].token_count == 10
    assert len(chunks[2].segment_ids) == 1


def test_chunking_with_overlap():
    counter = DummyCounter()
    
    segments = [
        CanonicalSegment(0.0, 1.0, "word " * 10),
        CanonicalSegment(1.0, 2.0, "word " * 10),
        CanonicalSegment(2.0, 3.0, "word " * 10),
    ]
    uuids = [uuid.uuid4() for _ in segments]
    
    # Max 25, overlap 15
    # Chunk 1: Seg 1 (10) + Seg 2 (10) = 20 tokens.
    # Overlap allows keeping Seg 2 (10 tokens).
    # Chunk 2: (Overlap Seg 2: 10) + Seg 3 (10) = 20 tokens.
    
    chunks = create_semantic_chunks(segments, uuids, max_tokens=25, overlap_tokens=15, token_counter=counter)
    
    assert len(chunks) == 2
    
    # Chunk 1 has seg 1 and 2
    assert chunks[0].segment_ids == [uuids[0], uuids[1]]
    
    # Chunk 2 has seg 2 and 3
    assert chunks[1].segment_ids == [uuids[1], uuids[2]]


def test_speaker_boundary_splitting():
    counter = DummyCounter()
    
    segments = [
        CanonicalSegment(0.0, 1.0, "word " * 15, speaker="A"), # 15 tokens
        CanonicalSegment(1.0, 2.0, "word " * 10, speaker="B"), # 10 tokens, Speaker change!
        CanonicalSegment(2.0, 3.0, "word " * 10, speaker="B"), # 10 tokens
    ]
    uuids = [uuid.uuid4() for _ in segments]
    
    # max_tokens = 28. 
    # Seg 1 (15) + Seg 2 (10) = 25 <= 28, so no hard size split.
    # But Seg 1 (15) > 28 * 0.5 (14), and speaker changes A->B, so it should split early!
    
    chunks = create_semantic_chunks(segments, uuids, max_tokens=28, overlap_tokens=0, token_counter=counter)
    
    assert len(chunks) == 2
    assert chunks[0].segment_ids == [uuids[0]]
    assert chunks[1].segment_ids == [uuids[1], uuids[2]]
