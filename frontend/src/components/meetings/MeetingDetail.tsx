import React, { useEffect, useState, useCallback } from 'react';
import { useLocation } from 'react-router';
import { meetingsApi } from '../../api/meetings';
import { useJobPolling } from '../../hooks/useJobPolling';
import type { Meeting } from '../../types/meeting';
import { JobStatusDisplay } from './JobStatusDisplay';
import { TranscriptViewer } from './TranscriptViewer';
import './meetings.css';

interface MeetingDetailProps {
  meetingId: string;
}

export function MeetingDetail({ meetingId }: MeetingDetailProps) {
  const location = useLocation();
  const stateJobId = location.state?.jobId as string | undefined;

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchMeeting = useCallback(async () => {
    try {
      setLoading(true);
      const data = await meetingsApi.get(meetingId);
      setMeeting(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch meeting'));
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  useEffect(() => {
    fetchMeeting();
  }, [fetchMeeting]);

  // Polling Job if we have a Job ID and the meeting is not ready or failed
  const { job } = useJobPolling(
    (meeting?.status !== 'ready' && meeting?.status !== 'failed') ? stateJobId : undefined,
    fetchMeeting
  );

  // Fallback meeting polling when no jobId exists and meeting is not terminal
  useEffect(() => {
    if (stateJobId) return; // Mutually exclusive with job polling
    if (!meeting) return;
    
    if (meeting.status === 'ready' || meeting.status === 'failed') return;
    
    let timeoutId: number;
    const pollMeeting = async () => {
      try {
        const data = await meetingsApi.get(meetingId);
        setMeeting(data);
        if (data.status === 'ready' || data.status === 'failed') {
          return;
        }
        timeoutId = window.setTimeout(pollMeeting, 3000);
      } catch (err) {
        timeoutId = window.setTimeout(pollMeeting, 5000);
      }
    };
    
    timeoutId = window.setTimeout(pollMeeting, 3000);
    
    return () => window.clearTimeout(timeoutId);
  }, [meeting?.status, meetingId, stateJobId]);

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
    </div>
  );
}
