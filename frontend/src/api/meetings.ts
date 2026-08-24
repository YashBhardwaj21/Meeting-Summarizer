import { api } from './client';
import type { Meeting } from '../types/meeting';

export const meetingsApi = {
  listByChat: (chatId: string) =>
    api.get<Meeting[]>(`/chats/${chatId}/meetings`),

  get: (meetingId: string) =>
    api.get<Meeting>(`/meetings/${meetingId}`),

  create: (chatId: string, fileId: string) =>
    api.post<{ meeting: Meeting; job_id: string; job_status: string }>(
      `/chats/${chatId}/meetings`,
      { file_id: fileId }
    ),

  rename: (meetingId: string, title: string) =>
    api.patch<Meeting>(
      `/meetings/${meetingId}`,
      { title }
    ),
};
