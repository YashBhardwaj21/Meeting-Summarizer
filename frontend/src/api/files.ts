import { api } from './client';
import type { FileResponse } from '../types/file';

export const filesApi = {
  presign: (chatId: string, filename: string, contentType: string, sizeBytes: number) => 
    api.post<{ file_id: string; upload_url: string; expires_in: number }>(`/chats/${chatId}/uploads/presign`, {
      filename,
      content_type: contentType,
      size_bytes: sizeBytes
    }),
    
  complete: (chatId: string, fileId: string) => 
    api.post<FileResponse>(`/chats/${chatId}/files/${fileId}/complete`),
};
