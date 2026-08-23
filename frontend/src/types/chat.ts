export interface Chat {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  file_count: number;
  meeting_count: number;
}

export interface ChatCreate {
  title?: string;
}

export interface ChatSource {
  meeting_id: string;
  chunk_id: string;
  start_time: number;
  end_time: number;
  speaker?: string | null;
  speakers?: string[];
  segments?: any[];
  text: string;
}

export type ChatMessageRole = 'user' | 'assistant' | 'system';
export type ChatMessageType = 'text' | 'meeting';

export interface ChatMessage {
  id: string;
  chat_id: string;
  role: ChatMessageRole;
  message_type: ChatMessageType;
  content: string | null;
  created_at: string;
  status?: 'pending' | 'processing' | 'complete' | 'error';
  meeting_id?: string | null;
  metadata?: {
    filename: string;
    size_bytes: number;
    job_id?: string | null;
  };
  sources?: ChatSource[];
}

export interface AskQuestionResponse {
  message: ChatMessage;
  sources?: ChatSource[];
}
