import React from 'react';
import { useParams } from 'react-router';
import { useMeetings } from '../hooks/useMeetings';
import { MeetingMetrics } from '../components/meetings/MeetingMetrics';
import { MeetingList } from '../components/meetings/MeetingList';
import { ChatComposer } from '../components/composer/ChatComposer';
import { ChatMessageList } from '../components/chat/ChatMessageList';
import '../components/meetings/meetings.css';
import '../components/chat/chat.css';

export function ChatRoute() {
  const { chatId } = useParams();
  const { meetings, loading } = useMeetings(chatId);

  return (
    <div className="chat-workspace">
      <div className="chat-content">
        <ChatMessageList chatId={chatId} />
        
        {/* Secondary context area */}
        <div className="workspace-context" style={{ marginTop: '40px', borderTop: '1px solid var(--border)', paddingTop: '24px', paddingLeft: '16px', paddingRight: '16px' }}>
          <h2>Workspace Context</h2>
          <MeetingMetrics meetings={meetings} />
          
          <h3 style={{ marginTop: '24px' }}>Meetings</h3>
          <div style={{ marginTop: '16px' }}>
            <MeetingList meetings={meetings} loading={loading} />
          </div>
        </div>
      </div>

      <div className="chat-composer-container">
        <ChatComposer chatId={chatId} />
      </div>
    </div>
  );
}
