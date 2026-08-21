import { api } from './client';

export interface StorageUsageResponse {
  used_bytes: number;
  quota_bytes: number;
  used_percent: number;
}

export const storageApi = {
  getUsage: (chatId: string) => api.get<StorageUsageResponse>(`/chats/${chatId}/storage`),
};
