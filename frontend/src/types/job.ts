export type JobStatusType = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface Job {
  id: string;
  meeting_id: string;
  status: JobStatusType;
  stage: string | null;
  attempt_count: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}
