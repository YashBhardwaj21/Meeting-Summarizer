import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useChats } from '../hooks/useChats';
import '../components/layout/layout.css';

export function RootRoute() {
  const { createChat } = useChats();
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNewChat = async () => {
    try {
      setIsCreating(true);
      setError(null);
      const newChat = await createChat();
      navigate(`/chats/${newChat.id}`);
    } catch (err) {
      setError('Failed to create workspace. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: '1rem', color: 'var(--color-text-primary)' }}>Start a meeting workspace</h2>
        <button 
          className="btn-new-chat" 
          onClick={handleNewChat} 
          disabled={isCreating}
          style={{ width: 'auto', padding: '12px 24px', fontSize: '1.1rem' }}
        >
          {isCreating ? 'Creating...' : '+ New Chat'}
        </button>
        {error && <div className="upload-error" style={{ marginTop: '1rem' }}>{error}</div>}
      </div>
    </div>
  );
}
