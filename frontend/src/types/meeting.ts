export type MeetingStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface Meeting {
  id: string;
  chat_id: string;
  file_id: string;
  title: string | null;
  status: MeetingStatus;
  duration_seconds: number | null;
  created_at: string;
}
