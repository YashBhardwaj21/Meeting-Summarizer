import React from 'react';
import { useNavigate } from 'react-router';
import type { Meeting } from '../../types/meeting';

interface MeetingCardProps {
  meeting: Meeting;
}

export function MeetingCard({ meeting }: MeetingCardProps) {
  const navigate = useNavigate();

  const handleView = () => {
    navigate(`/meetings/${meeting.id}`);
  };

  const dateStr = new Date(meeting.created_at).toLocaleDateString(
    'en-GB',
    {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }
  );

  const durationStr = meeting.duration_seconds
    ? `${Math.floor(meeting.duration_seconds / 60)}m`
    : 'Unknown';

  const isReady = meeting.status === 'ready';
  const isProcessing = meeting.status === 'processing';
  const isFailed = meeting.status === 'failed';

  return (
    <div className="meeting-card">
      <div className="meeting-icon">
        {isReady && '▶'}
        {isProcessing && '◌'}
        {isFailed && '!'}
        {meeting.status === 'pending' && '⋯'}
      </div>

      <div className="meeting-content">
        <h3 className="meeting-title">
          {meeting.title || 'Untitled Meeting'}
        </h3>

        <div className="meeting-meta">
          {dateStr} &bull; {durationStr} &bull; Media
        </div>
      </div>

      <div className="meeting-status">
        <span className={`status-badge status-${meeting.status}`}>
          {meeting.status.toUpperCase()}
        </span>
      </div>

      <div className="meeting-action">
        <button
          className="btn-view"
          onClick={handleView}
        >
          {isFailed ? '[View details]' : '[View]'}
        </button>
      </div>
    </div>
  );
}
