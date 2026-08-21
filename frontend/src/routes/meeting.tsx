import React from 'react';
import { useParams } from 'react-router';

export function MeetingRoute() {
  const { meetingId } = useParams();
  return (
    <div className="meeting-detail">
      <h2>Meeting Detail: {meetingId}</h2>
      <p className="text-muted">This is where the transcript and processing status will go.</p>
    </div>
  );
}
