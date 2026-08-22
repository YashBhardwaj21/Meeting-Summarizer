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
  speaker: string;
  text: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources?: ChatSource[];
  status?: 'pending' | 'complete' | 'error';
}

export interface AskQuestionResponse {
  message: ChatMessage;
  sources?: ChatSource[];
}
