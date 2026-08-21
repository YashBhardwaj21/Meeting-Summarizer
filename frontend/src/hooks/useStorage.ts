import { useState, useEffect, useCallback } from 'react';
import { storageApi } from '../api/storage';

export function useStorage(chatId: string | undefined) {
  const [usedBytes, setUsedBytes] = useState<number>(0);
  const [quotaBytes, setQuotaBytes] = useState<number>(0);
  const [usedPercent, setUsedPercent] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStorage = useCallback(async () => {
    if (!chatId) {
      setUsedBytes(0);
      setQuotaBytes(0);
      setUsedPercent(0);
      setError(null);
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      const data = await storageApi.getUsage(chatId);
      setUsedBytes(data.used_bytes);
      setQuotaBytes(data.quota_bytes);
      setUsedPercent(data.used_percent);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch storage usage'));
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    fetchStorage();
  }, [fetchStorage]);

  return {
    usedBytes,
    quotaBytes,
    usedPercent,
    loading,
    error,
    refetch: fetchStorage
  };
}
