import { useState, useEffect, useCallback, useRef } from 'react';
import { transcriptsApi } from '../api/transcripts';
import type { TranscriptSegment } from '../types/transcript';

export function useTranscripts(chatId: string | undefined, meetingId: string | undefined, isReady: boolean) {
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const offsetRef = useRef(0);
  const loadingRef = useRef(false);
  const limit = 50;

  const fetchTranscripts = useCallback(async (isLoadMore = false) => {
    if (!chatId || !meetingId || !isReady) return;
    if (loadingRef.current) return;

    try {
      loadingRef.current = true;
      setLoading(true);
      setError(null);
      
      const currentOffset = isLoadMore ? offsetRef.current : 0;
      const data = await transcriptsApi.get(chatId, meetingId, currentOffset, limit);
      
      setTotal(data.total);
      
      if (isLoadMore) {
        setSegments(prev => {
          // Avoid duplicates in case of strict mode double mounts
          const existingIds = new Set(prev.map(s => s.id));
          const newSegments = data.items.filter(s => !existingIds.has(s.id));
          return [...prev, ...newSegments];
        });
      } else {
        setSegments(data.items);
      }
      
      setHasMore(currentOffset + data.items.length < data.total);
      offsetRef.current = currentOffset + data.items.length;
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch transcript'));
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [chatId, meetingId, isReady]);

  useEffect(() => {
    // Initial fetch when meeting becomes ready
    if (isReady && meetingId && chatId) {
      offsetRef.current = 0;
      fetchTranscripts(false);
    }
  }, [isReady, meetingId, chatId, fetchTranscripts]);

  const loadMore = () => {
    if (!loadingRef.current && hasMore) {
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
