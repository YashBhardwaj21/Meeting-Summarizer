import React, { useEffect, useRef } from 'react';
import { useChatMessages } from '../../hooks/useChatMessages';
import { ChatMessage } from './ChatMessage';

interface ChatMessageListProps {
  chatId?: string;
}

export function ChatMessageList({ chatId }: ChatMessageListProps) {
  const { messages, loading, asking, loadMessages } = useChatMessages(chatId);
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
      <div className="chat-message-list empty-state">
        <h3>What would you like to know?</h3>
        <p>Upload a meeting recording to get started, or ask a question if you already have one.</p>
      </div>
    );
  }

  return (
    <div className="chat-message-list">
      {messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} />
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
