import { useState, useEffect, useCallback } from 'react';
import { transcriptsApi } from '../api/transcripts';
import type { TranscriptSegment } from '../types/transcript';

export function useTranscripts(meetingId: string | undefined, isReady: boolean) {
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const limit = 50;

  const fetchTranscripts = useCallback(async (isLoadMore = false) => {
    if (!meetingId || !isReady) return;

    try {
      setLoading(true);
      setError(null);
      const data = await transcriptsApi.get(meetingId, isLoadMore ? skip : 0, limit);
      
      setTotal(data.total_segments);
      
      if (isLoadMore) {
        setSegments(prev => [...prev, ...data.segments]);
      } else {
        setSegments(data.segments);
      }
      
      setHasMore(isLoadMore ? (skip + limit < data.total_segments) : (limit < data.total_segments));
      if (!isLoadMore) {
        setSkip(limit);
      } else {
        setSkip(prev => prev + limit);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch transcript'));
    } finally {
      setLoading(false);
    }
  }, [meetingId, isReady, skip]);

  useEffect(() => {
    // Initial fetch when meeting becomes ready
    if (isReady && meetingId && segments.length === 0) {
      fetchTranscripts(false);
    }
  }, [isReady, meetingId]); // Intentionally omitting segments and fetchTranscripts

  const loadMore = () => {
    if (!loading && hasMore) {
      fetchTranscripts(true);
    }
  };

  return {
    segments,
    loading,
    error,
    hasMore,
    total,
    loadMore,
  };
}
