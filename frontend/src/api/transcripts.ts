import { api } from './client';
import type { TranscriptResponse } from '../types/transcript';

export const transcriptsApi = {
  get: (meetingId: string, skip: number = 0, limit: number = 100) => 
    api.get<TranscriptResponse>(`/meetings/${meetingId}/transcripts?skip=${skip}&limit=${limit}`),
};
