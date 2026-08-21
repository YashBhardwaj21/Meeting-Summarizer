import { useState, useEffect, useCallback } from 'react';
import { meetingsApi } from '../api/meetings';
import type { Meeting } from '../types/meeting';

export function useMeetings(chatId: string | undefined) {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchMeetings = useCallback(async () => {
    if (!chatId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await meetingsApi.listByChat(chatId);
      setMeetings(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch meetings'));
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  return {
    meetings,
    loading,
    error,
    refetch: fetchMeetings,
  };
}
