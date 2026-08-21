import React, { useState } from 'react';
import { useParams } from 'react-router';
import { useMeetings } from '../hooks/useMeetings';
import { MeetingMetrics } from '../components/meetings/MeetingMetrics';
import { MeetingList } from '../components/meetings/MeetingList';
import { UploadModal } from '../components/upload/UploadModal';
import '../components/meetings/meetings.css';

export function ChatRoute() {
  const { chatId } = useParams();
  const { meetings, loading } = useMeetings(chatId);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  return (
    <div className="chat-workspace">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>Workspace Overview</h2>
        <button 
          className="btn-new-chat" 
          style={{ width: 'auto', padding: '10px 24px' }}
          onClick={() => setIsUploadModalOpen(true)}
        >
          Upload Media
        </button>
      </div>
      
      <MeetingMetrics meetings={meetings} />
      
      <h3>Recent Meetings</h3>
      <div style={{ marginTop: '16px' }}>
        <MeetingList meetings={meetings} loading={loading} />
      </div>

      {chatId && (
        <UploadModal 
          chatId={chatId} 
          isOpen={isUploadModalOpen} 
          onClose={() => setIsUploadModalOpen(false)} 
        />
      )}
    </div>
  );
}
