import React from 'react';
import { useParams } from 'react-router';
import { MeetingDetail } from '../components/meetings/MeetingDetail';

export function MeetingRoute() {
  const { meetingId } = useParams();
  
  if (!meetingId) return null;

  return <MeetingDetail meetingId={meetingId} />;
}
