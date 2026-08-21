import React from 'react';
import type { Meeting } from '../../types/meeting';

interface MeetingMetricsProps {
  meetings: Meeting[];
}

export function MeetingMetrics({ meetings }: MeetingMetricsProps) {
  const totalMeetings = meetings.length;
  
  const totalDurationSeconds = meetings.reduce((acc, m) => acc + (m.duration_seconds || 0), 0);
  const hours = Math.floor(totalDurationSeconds / 3600);
  const minutes = Math.floor((totalDurationSeconds % 3600) / 60);
  const durationString = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  const readyCount = meetings.filter(m => m.status === 'ready').length;
  const processingCount = meetings.filter(m => m.status === 'processing').length;

  return (
    <div className="metrics-container">
      <div className="metric-card">
        <div className="metric-value">{totalMeetings}</div>
        <div className="metric-label">meetings</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{durationString}</div>
        <div className="metric-label">duration</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{readyCount}</div>
        <div className="metric-label">ready</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{processingCount}</div>
        <div className="metric-label">processing</div>
      </div>
    </div>
  );
}
