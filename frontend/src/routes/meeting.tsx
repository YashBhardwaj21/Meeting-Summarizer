import React from 'react';
import { useParams } from 'react-router';
import { MeetingDetail } from '../components/meetings/MeetingDetail';

export function MeetingRoute() {
  const { chatId, meetingId } = useParams();
  
  if (!meetingId || !chatId) return null;

  return <MeetingDetail meetingId={meetingId} />;
}
