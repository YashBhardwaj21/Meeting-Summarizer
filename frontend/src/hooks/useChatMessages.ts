import { useState, useCallback } from 'react';
import { chatsApi } from '../api/chats';
import type { ChatMessage } from '../types/chat';

export type ChatMessagesController = {
  messages: ChatMessage[];
  loading: boolean;
  asking: boolean;
  error: Error | null;
  loadMessages: () => Promise<void>;
  askQuestion: (question: string) => Promise<void>;
  retryQuestion: (question: string) => void;
};

export function useChatMessages(chatId?: string): ChatMessagesController {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadMessages = useCallback(async () => {
    if (!chatId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await chatsApi.getMessages(chatId);
      setMessages(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load messages'));
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  const askQuestion = async (question: string) => {
    if (!chatId) return;
    
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      chat_id: chatId,
      role: 'user',
      message_type: 'text',
      content: question,
      created_at: new Date().toISOString(),
      status: 'complete'
    };
    
    setMessages(prev => [...prev, userMessage]);
    setAsking(true);
    setError(null);
    
    try {
      const response = await chatsApi.ask(chatId, question);
      setMessages(prev => [...prev, response.message]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to get an answer';
      const errorResponse: ChatMessage = {
        id: `error-${Date.now()}`,
        chat_id: chatId,
        role: 'assistant',
        message_type: 'text',
        content: `Error: ${errorMsg}. Please try asking again.`,
        created_at: new Date().toISOString(),
        status: 'error'
      };
      setMessages(prev => [...prev, errorResponse]);
      setError(err instanceof Error ? err : new Error(errorMsg));
    } finally {
      setAsking(false);
    }
  };

  const retryQuestion = (question: string) => {
    // Optionally remove the last error message before retrying
    setMessages(prev => prev.filter(m => m.status !== 'error'));
    askQuestion(question);
  };

  return {
    messages,
    loading,
    asking,
    error,
    loadMessages,
    askQuestion,
    retryQuestion,
  };
}
