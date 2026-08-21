import { api } from './client';

export const filesApi = {
  presign: (chatId: string, filename: string, contentType: string, sizeBytes: number) => 
    api.post<{ file_id: string; upload_url: string; expires_in: number }>(`/chats/${chatId}/files/presign`, {
      filename,
      content_type: contentType,
      size_bytes: sizeBytes
    }),
    
  complete: (fileId: string) => 
    api.post<void>(`/files/${fileId}/complete`),
};
