import { useState } from 'react';
import { filesApi } from '../api/files';
import { meetingsApi } from '../api/meetings';
import { useNavigate } from 'react-router';

export function useUpload(chatId: string) {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  const navigate = useNavigate();

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setProgress(0);
    setError(null);

    try {
      // 1. Get presigned URL
      setProgress(10);
      const { file_id, upload_url } = await filesApi.presign(
        chatId,
        file.name,
        file.type || 'application/octet-stream',
        file.size
      );

      // 2. Upload directly to MinIO using XMLHttpRequest for progress tracking
      setProgress(20);
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', upload_url, true);
        
        // Let the browser set the content type correctly, but we can hint it
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
        
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            // Map 20% -> 80% for the actual upload phase
            const percentComplete = 20 + Math.round((e.loaded / e.total) * 60);
            setProgress(percentComplete);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error(`S3 Upload failed with status ${xhr.status}`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during S3 upload'));
        xhr.send(file);
      });

      // 3. Mark file as complete
      setProgress(85);
      await filesApi.complete(chatId, file_id);

      // 4. Create meeting
      setProgress(95);
      const response = await meetingsApi.create(chatId, file_id);
      
      setProgress(100);
      
      // Navigate to the meeting and pass jobId for polling
      navigate(`/meetings/${response.meeting.id}`, { state: { jobId: response.job_id } });
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Upload failed'));
      setIsUploading(false);
    }
  };

  return {
    uploadFile,
    isUploading,
    progress,
    error,
  };
}
