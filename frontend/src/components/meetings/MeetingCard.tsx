import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import type { Meeting } from '../../types/meeting';
import { meetingsApi } from '../../api/meetings';

interface MeetingCardProps {
  meeting: Meeting;
}

export function MeetingCard({ meeting }: MeetingCardProps) {
  const navigate = useNavigate();

  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(meeting.title || 'Untitled Meeting');
  const [saving, setSaving] = useState(false);

  const handleView = () => {
    if (!isEditing) {
      navigate(`/meetings/${meeting.id}`);
    }
  };

  const handleRename = async () => {
    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      setTitle(meeting.title || 'Untitled Meeting');
      setIsEditing(false);
      return;
    }

    if (trimmedTitle === (meeting.title || 'Untitled Meeting')) {
      setIsEditing(false);
      return;
    }

    try {
      setSaving(true);

      await meetingsApi.rename(meeting.id, trimmedTitle);

      setTitle(trimmedTitle);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to rename meeting:', error);
      setTitle(meeting.title || 'Untitled Meeting');
    } finally {
      setSaving(false);
    }
  };

  const handleTitleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      void handleRename();
    }

    if (event.key === 'Escape') {
      setTitle(meeting.title || 'Untitled Meeting');
      setIsEditing(false);
    }
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
        {isEditing ? (
          <input
            autoFocus
            value={title}
            maxLength={255}
            disabled={saving}
            onChange={(event) => setTitle(event.target.value)}
            onBlur={() => void handleRename()}
            onKeyDown={handleTitleKeyDown}
            className="meeting-title-input"
          />
        ) : (
          <h3 
            className="meeting-title"
            onDoubleClick={(event) => {
              event.stopPropagation();
              setIsEditing(true);
            }}
            title="Double click to rename"
          >
            {title}
          </h3>
        )}

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
