import React from 'react';
import { useParams } from 'react-router';
import { useMeetings } from '../hooks/useMeetings';
import { MeetingMetrics } from '../components/meetings/MeetingMetrics';
import { MeetingList } from '../components/meetings/MeetingList';
import { MeetingComposer } from '../components/composer/MeetingComposer';
import '../components/meetings/meetings.css';

export function ChatRoute() {
  const { chatId } = useParams();
  const { meetings, loading } = useMeetings(chatId);

  return (
    <div className="chat-workspace">
      <div style={{ marginBottom: '32px' }}>
        <MeetingComposer chatId={chatId} />
      </div>
      
      <h2>Workspace Overview</h2>
      <MeetingMetrics meetings={meetings} />
      
      <h3>Recent Meetings</h3>
      <div style={{ marginTop: '16px' }}>
        <MeetingList meetings={meetings} loading={loading} />
      </div>
    </div>
  );
}
