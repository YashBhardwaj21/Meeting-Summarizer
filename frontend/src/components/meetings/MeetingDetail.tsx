import React, { useEffect, useState, useCallback } from 'react';
import { useChatMessages } from '../../hooks/useChatMessages';
import { meetingsApi } from '../../api/meetings';
import { jobsApi } from '../../api/jobs';
import { useJobPolling } from '../../hooks/useJobPolling';
import type { Meeting } from '../../types/meeting';
import { JobStatusDisplay } from './JobStatusDisplay';
import { TranscriptViewer } from './TranscriptViewer';
import { ChatComposer } from '../composer/ChatComposer';
import './meetings.css';

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | undefined>(undefined);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const chatMessages = useChatMessages(meeting?.chat_id);

  const fetchMeeting = useCallback(async () => {
    try {
      setLoading(true);
      const data = await meetingsApi.get(meetingId);
      setMeeting(data);
      
      if (data.status !== 'ready' && data.status !== 'failed' && data.status !== 'cancelled') {
        try {
          const jobData = await jobsApi.getByMeetingId(meetingId);
          setActiveJobId(jobData.id);
        } catch (jobErr) {
          console.error("Failed to fetch active job for meeting", jobErr);
        }
      } else {
        setActiveJobId(undefined);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch meeting'));
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  useEffect(() => {
    fetchMeeting();
  }, [fetchMeeting]);

  // Polling Job if we have an active Job ID
  const { job } = useJobPolling(activeJobId, fetchMeeting);

  if (loading && !meeting) {
    return <div className="text-muted">Loading meeting details...</div>;
  }

  if (error || !meeting) {
    return <div className="upload-error">{error?.message || 'Meeting not found'}</div>;
  }

  const dateStr = new Date(meeting.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  const durationStr = meeting.duration_seconds 
    ? `${Math.floor(meeting.duration_seconds / 60)}m ${Math.round(meeting.duration_seconds % 60)}s` 
    : 'Unknown';

  const isReady = meeting.status === 'ready';

  return (
    <div className="meeting-detail-container">
      <div className="meeting-detail-header">
        <h1>{meeting.title || 'Untitled Meeting'}</h1>
        <div className="meeting-meta-large">
          <span>{dateStr}</span>
          <span>&bull;</span>
          <span>{durationStr}</span>
        </div>
      </div>

      {job && <JobStatusDisplay job={job} />}
      
      {meeting.status === 'processing' && !job && (
        <div className="job-status-card">
          <div className="job-progress">
            <div className="spinner"></div>
            <div className="job-stage">Processing in background...</div>
          </div>
        </div>
      )}

      <TranscriptViewer 
        chatId={meeting.chat_id}
        meetingId={meeting.id} 
        status={meeting.status} 
      />
      
      <div style={{ marginTop: '40px' }}>
        {meeting.chat_id && (
          <ChatComposer 
            chatId={meeting.chat_id} 
            chatMessages={chatMessages}
            selectedFile={selectedFile}
            setSelectedFile={setSelectedFile}
          />
        )}
      </div>
    </div>
  );
}
