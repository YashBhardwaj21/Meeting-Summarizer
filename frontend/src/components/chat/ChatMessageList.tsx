import React, { useEffect, useRef } from 'react';
import type { ChatMessagesController } from '../../hooks/useChatMessages';
import { useMeetingJobStatuses } from '../../hooks/useMeetingJobStatuses';
import { ChatMessage } from './ChatMessage';

interface ChatMessageListProps {
  chatId?: string;
  chatMessages: ChatMessagesController;
  selectedFile?: File | null;
}

export function ChatMessageList({ chatId, chatMessages, selectedFile }: ChatMessageListProps) {
  const { messages, loading, asking, error, loadMessages, retryQuestion } = chatMessages;
  const jobs = useMeetingJobStatuses(messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatId) {
      loadMessages();
    }
  }, [chatId, loadMessages]);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, asking]);

  if (loading && messages.length === 0) {
    return (
      <div className="chat-message-list empty">
        <div className="skeleton" style={{ height: '60px', width: '80%', marginBottom: '16px' }}></div>
        <div className="skeleton" style={{ height: '100px', width: '90%' }}></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chat-message-list error-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '1rem', color: 'var(--color-danger)' }}>
        <p>Unable to load this chat.</p>
        <button className="btn-secondary" onClick={() => loadMessages()}>
          Retry
        </button>
      </div>
    );
  }

  if (messages.length === 0 && !asking && !loading && !error) {
    return (
      <div className="chat-message-list empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-secondary)', textAlign: 'center' }}>
        {!selectedFile ? (
          <>
            <h2>No file</h2>
            <p>What would you like to work on?</p>
          </>
        ) : (
          <>
            <h2>File selected: {selectedFile.name}</h2>
            <p>Ready to upload. Press Enter to upload your recording.</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="chat-message-list">
      {messages.map(msg => (
        <ChatMessage 
          key={msg.id} 
          message={msg} 
          job={msg.meeting_id ? jobs[msg.meeting_id] : undefined} 
          onRetry={retryQuestion}
        />
      ))}
      {asking && (
        <div className="chat-message message-assistant asking">
          <div className="message-header"><strong>Assistant</strong></div>
          <div className="message-content">Thinking...</div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
