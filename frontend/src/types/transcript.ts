export interface TranscriptSegment {
  id: string;
  speaker: string | null;
  start_time: number;
  end_time: number;
  text: string;
}

export interface TranscriptResponse {
  meeting_id: string;
  total_segments: number;
  segments: TranscriptSegment[];
}
