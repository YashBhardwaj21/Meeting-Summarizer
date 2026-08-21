export interface TranscriptSegment {
  id: string;
  sequence: number;
  speaker: string | null;
  start_time: number;
  end_time: number;
  text: string;
}

export interface TranscriptResponse {
  items: TranscriptSegment[];
  total: number;
  offset: number;
  limit: number;
}
