import React from 'react';
import { useParams } from 'react-router';

export function ChatRoute() {
  const { chatId } = useParams();
  return (
    <div className="chat-workspace">
      <h2>Chat Workspace: {chatId}</h2>
      <p className="text-muted">This is where the meeting list and upload button will go.</p>
    </div>
  );
}
