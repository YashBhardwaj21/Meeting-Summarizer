import React, { useState } from 'react';
import { useParams } from 'react-router';
import { ChatComposer } from '../components/composer/ChatComposer';
import { ChatMessageList } from '../components/chat/ChatMessageList';
import { useChatMessages } from '../hooks/useChatMessages';
import '../components/meetings/meetings.css';
import '../components/chat/chat.css';

export function ChatRoute() {
  const { chatId } = useParams();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const chatMessages = useChatMessages(chatId);

  return (
    <div className="chat-workspace">
      <div className="chat-content">
        <ChatMessageList 
          chatId={chatId} 
          chatMessages={chatMessages} 
          selectedFile={selectedFile}
        />
      </div>

      <div className="chat-composer-container">
        <ChatComposer 
          chatId={chatId} 
          chatMessages={chatMessages} 
          selectedFile={selectedFile}
          setSelectedFile={setSelectedFile}
        />
      </div>
    </div>
  );
}
