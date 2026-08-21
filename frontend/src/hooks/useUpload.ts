import { useState } from 'react';
import { chatsApi } from '../api/chats';
import { filesApi } from '../api/files';
import { meetingsApi } from '../api/meetings';
import { useNavigate } from 'react-router';

const SUPPORTED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.mov', '.mkv'];
const MIME_MAP: Record<string, string> = {
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.m4a': 'audio/mp4',
  '.ogg': 'audio/ogg',
  '.mp4': 'video/mp4',
  '.mov': 'video/quicktime',
  '.mkv': 'video/x-matroska'
};

export type UploadStatus = 'idle' | 'presigning' | 'uploading' | 'confirming' | 'starting' | 'processing' | 'complete' | 'error';

export function useUpload(chatId?: string) {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [error, setError] = useState<Error | null>(null);
  const navigate = useNavigate();

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setProgress(null);
    setStatus('uploading');
    setError(null);

    try {
      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      if (!SUPPORTED_EXTENSIONS.includes(ext)) {
        throw new Error(`Unsupported file type. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
      }

      const mimeType = MIME_MAP[ext] || 'application/octet-stream';

      let activeChatId = chatId;
      if (!activeChatId) {
        const chat = await chatsApi.create({});
        activeChatId = chat.id;
      }

      setStatus('presigning');
      const { file_id, upload_url } = await filesApi.presign(
        activeChatId,
        file.name,
        mimeType,
        file.size
      );

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', upload_url, true);
        xhr.setRequestHeader('Content-Type', mimeType);
        
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            setProgress(Math.round((e.loaded / e.total) * 100));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else if (xhr.status === 403) {
            reject(new Error('Upload returned HTTP 403 (CORS or Signature mismatch)'));
          } else if (xhr.status === 400) {
            reject(new Error('Upload returned HTTP 400'));
          } else if (xhr.status >= 500) {
            reject(new Error('Upload returned HTTP 500'));
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error('Unable to reach the upload service. Check the upload URL, MinIO availability, and CORS configuration.'));
        xhr.onabort = () => reject(new Error('Upload was cancelled.'));
        xhr.ontimeout = () => reject(new Error('Upload timed out.'));
        
        setStatus('uploading');
        xhr.send(file);
      });

      setStatus('confirming');
      setProgress(null);
      await filesApi.complete(activeChatId, file_id);

      setStatus('starting');
      const response = await meetingsApi.create(activeChatId, file_id);
      
      setStatus('complete');
      
      // Navigate to the meeting and pass jobId for polling
      navigate(`/chats/${activeChatId}/meetings/${response.meeting.id}`, { state: { jobId: response.job_id } });
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Upload failed'));
      setStatus('error');
      setIsUploading(false);
    }
  };

  return {
    uploadFile,
    isUploading,
    progress,
    status,
    error,
  };
}
