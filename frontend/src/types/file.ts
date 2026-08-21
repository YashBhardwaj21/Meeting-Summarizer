export type MediaType = 'audio' | 'video';
export type UploadStatus = 'pending' | 'uploaded' | 'failed';

export interface FileResponse {
  id: string;
  filename: string;
  media_type: MediaType;
  mime_type: string;
  size_bytes: number;
  upload_status: UploadStatus;
  created_at: string;
}
