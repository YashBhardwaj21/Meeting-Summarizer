import React, { useEffect, useRef } from 'react';
import { useChatMessages } from '../../hooks/useChatMessages';
import { useMeetingJobStatuses } from '../../hooks/useMeetingJobStatuses';
import { ChatMessage } from './ChatMessage';

interface ChatMessageListProps {
  chatId?: string;
  chatMessages: ReturnType<typeof useChatMessages>;
  selectedFile?: File | null;
}

export function ChatMessageList({ chatId, chatMessages, selectedFile }: ChatMessageListProps) {
  const { messages, loading, asking, loadMessages } = chatMessages;
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

  if (messages.length === 0 && !asking) {
    return (
      <div className="chat-message-list">
        {/* Empty chat timeline */}
      </div>
    );
  }

  return (
    <div className="chat-message-list">
      {messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} job={msg.meeting_id ? jobs[msg.meeting_id] : undefined} />
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
