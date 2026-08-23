import React from 'react';
import { Link } from 'react-router';
import type { ChatMessage } from '../../types/chat';
import type { Job } from '../../types/job';
import { jobsApi } from '../../api/jobs';
import { TranscriptViewer } from '../meetings/TranscriptViewer';
import './chat.css';

interface MeetingMessageProps {
  message: ChatMessage;
  job?: Job;
}

export function MeetingMessage({ message, job }: MeetingMessageProps) {
  const [showTranscript, setShowTranscript] = React.useState(false);

  if (!message.metadata) return null;

  const { filename, size_bytes } = message.metadata;
  const status: string = job?.status || 'queued';
  
  const formatSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const handleCancel = async () => {
    if (job) {
      try {
        await jobsApi.cancel(job.id);
      } catch (err) {
        console.error('Failed to cancel job', err);
      }
    }
  };

  return (
    <div className="chat-message message-assistant meeting-event">
      <div className="message-header"><strong>You</strong></div>
      <div className="meeting-bubble">
        <div className="meeting-bubble-body">
          <div className="meeting-bubble-file">{filename}</div>
          <div className="meeting-bubble-meta">
            {formatSize(size_bytes)}
          </div>
          {(status === 'queued' || status === 'processing') && (
            <div className="meeting-bubble-stage">
              {status === 'queued' ? 'Waiting for processing worker...' : (job?.stage || 'Processing...')}
            </div>
          )}
          {status === 'failed' && (
            <div className="meeting-bubble-stage" style={{ color: 'var(--color-red)' }}>
              Processing failed: {job?.error_message || 'Unknown error'}
            </div>
          )}
          {status === 'cancelled' && (
            <div className="meeting-bubble-stage" style={{ color: 'var(--color-text-muted)' }}>
              Processing cancelled.
            </div>
          )}
        </div>
        
        {(status === 'queued' || status === 'processing') && (
          <div className="meeting-bubble-footer" style={{ justifyContent: 'flex-start' }}>
             <button className="btn-cancel-meeting" onClick={handleCancel}>Cancel</button>
          </div>
        )}

        {status === 'completed' && message.meeting_id && (
          <div className="meeting-bubble-footer">
            <span className="status-completed-text">Transcript ready</span>
            <button className="view-transcript-link" onClick={() => setShowTranscript(!showTranscript)}>
              {showTranscript ? 'Hide transcript' : 'View transcript'}
            </button>
          </div>
        )}

        {showTranscript && status === 'completed' && message.meeting_id && (
          <div className="inline-transcript-container">
            <TranscriptViewer 
              chatId={message.chat_id}
              meetingId={message.meeting_id}
              status={status}
            />
          </div>
        )}
      </div>
    </div>
  );
}
