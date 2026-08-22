import { useState, useEffect, useCallback } from 'react';
import { chatsApi } from '../api/chats';
import type { Chat } from '../types/chat';

export function useChats() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchChats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await chatsApi.list();
      setChats(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch chats'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchChats();
  }, [fetchChats]);

  const createChat = async (title?: string) => {
    try {
      setCreating(true);
      const newChat = await chatsApi.create(title ? { title } : undefined);
      setChats(prev => [newChat, ...prev]);
      return newChat;
    } finally {
      setCreating(false);
    }
  };

  return {
    chats,
    loading,
    creating,
    error,
    refetch: fetchChats,
    createChat,
  };
}
