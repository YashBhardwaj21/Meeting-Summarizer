import { api } from './client';
import type { Chat, ChatCreate } from '../types/chat';

export const chatsApi = {
  list: () => api.get<Chat[]>('/chats'),
  get: (chatId: string) => api.get<Chat>(`/chats/${chatId}`),
  create: (data?: ChatCreate) => api.post<Chat>('/chats', data),
};
