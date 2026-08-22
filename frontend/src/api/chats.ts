import { api } from './client';
import type { Chat, ChatCreate, AskQuestionResponse, ChatMessage } from '../types/chat';

export const chatsApi = {
  list: () => api.get<Chat[]>('/chats'),
  get: (chatId: string) => api.get<Chat>(`/chats/${chatId}`),
  create: (data: ChatCreate = {}) => api.post<Chat>('/chats', data),
  delete: (chatId: string) => api.delete(`/chats/${chatId}`),
  ask: (chatId: string, question: string, limit = 10) => 
    api.post<AskQuestionResponse>(`/chats/${chatId}/ask`, { question, limit }),
  getMessages: (chatId: string) => api.get<ChatMessage[]>(`/chats/${chatId}/messages`),
};
