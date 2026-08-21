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
