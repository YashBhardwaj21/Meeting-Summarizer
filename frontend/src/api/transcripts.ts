import { api } from './client';
import type { TranscriptResponse } from '../types/transcript';

export const transcriptsApi = {
  get: (chatId: string, meetingId: string, offset: number = 0, limit: number = 50) => 
    api.get<TranscriptResponse>(`/chats/${chatId}/meetings/${meetingId}/transcript?offset=${offset}&limit=${limit}`),
};
