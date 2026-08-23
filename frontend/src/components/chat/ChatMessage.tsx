import React from 'react';
import type { ChatMessage as ChatMessageType } from '../../types/chat';
import type { Job } from '../../types/job';
import { MeetingMessage } from './MeetingMessage';

interface ChatMessageProps {
  message: ChatMessageType;
  job?: Job;
}

export function ChatMessage({ message, job }: ChatMessageProps) {
  if (message.message_type === 'meeting') {
    return <MeetingMessage message={message} job={job} />;
  }

  const isUser = message.role === 'user';
  
  return (
    <div className={`chat-message ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="message-header">
        <strong>{isUser ? 'User' : 'Assistant'}</strong>
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
