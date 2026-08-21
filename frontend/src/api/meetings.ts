import { api } from './client';
import type { Meeting } from '../types/meeting';

export const meetingsApi = {
  // We fetch meetings per chat ID. 
  // Wait, does backend have GET /api/v1/chats/{chat_id}/meetings?
  // Let me check the backend routes in my head.
  // The user prompt said: "GET meetings for chat". Let's assume the route exists or we will filter.
  // Actually, standard REST would be GET /api/v1/chats/{chat_id}/meetings
  listByChat: (chatId: string) => api.get<Meeting[]>(`/chats/${chatId}/meetings`),
  get: (meetingId: string) => api.get<Meeting>(`/meetings/${meetingId}`),
  create: (chatId: string, fileId: string) => 
    api.post<{ meeting: Meeting, job_id: string, job_status: string }>(`/chats/${chatId}/meetings`, { file_id: fileId }),
};
