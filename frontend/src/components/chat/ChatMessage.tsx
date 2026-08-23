import React from 'react';
import type { ChatMessage as ChatMessageType } from '../../types/chat';
import type { Job } from '../../types/job';
import { MeetingMessage } from './MeetingMessage';

interface ChatMessageProps {
  message: ChatMessageType;
  job?: Job;
  onRetry?: (text: string) => void;
}

export function ChatMessage({ message, job, onRetry }: ChatMessageProps) {
  if (message.message_type === 'meeting') {
    return <MeetingMessage message={message} job={job} />;
  }

  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  
  return (
    <div className={`chat-message ${isUser ? 'message-user' : 'message-assistant'} ${isError ? 'error-state' : ''}`}>
      <div className="message-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>{isUser ? 'User' : 'Assistant'}</strong>
        {isUser && onRetry && (
          <button 
            className="btn-secondary" 
            style={{ padding: '2px 8px', fontSize: '0.8rem' }}
            onClick={() => onRetry(message.content || '')}
            title="Resend this message"
          >
            ↻ Retry
          </button>
        )}
      </div>
      <div className="message-content">
        {message.content && message.content.split('\n').map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>
      
      {message.sources && message.sources.length > 0 && (
        <div className="message-sources">
          <div className="sources-header">Sources</div>
          <ul className="sources-list">
            {message.sources.map((source, i) => {
              const formatTime = (sec: number) => {
                const m = Math.floor(sec / 60);
                const s = Math.floor(sec % 60);
                return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
              };
              return (
                <li key={i} className="source-item">
                  <span className="source-time">{formatTime(source.start_time)}</span>
                  <span className="source-separator"> — </span>
                  <span className="source-speaker">{source.speaker || 'Speaker'}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
