import React from 'react';
import { NavLink, useNavigate } from 'react-router';
import { useChats } from '../../hooks/useChats';
import './layout.css';

export function Sidebar() {
  const { chats, loading, createChat } = useChats();
  const navigate = useNavigate();

  const handleNewChat = async () => {
    try {
      const newChat = await createChat();
      navigate(`/chats/${newChat.id}`);
    } catch (err) {
      console.error('Failed to create chat:', err);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="logo">[M] MeetSum</h1>
      </div>
      <div className="sidebar-actions">
        <button className="btn-new-chat" onClick={handleNewChat}>+ New Chat</button>
      </div>
      <div className="sidebar-search">
        <input type="text" placeholder="Search chats..." />
      </div>
      <div className="sidebar-nav">
        <h2 className="nav-heading">CHATS</h2>
        {loading ? (
          <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
          </div>
        ) : (
          <ul className="chat-list">
            {chats.map(chat => (
              <li key={chat.id}>
                <NavLink 
                  to={`/chats/${chat.id}`} 
                  className={({ isActive }) => `chat-item ${isActive ? 'active' : ''}`}
                  style={{ display: 'block' }}
                >
                  <div className="chat-name">{chat.title || 'Untitled Workspace'}</div>
                  <div className="chat-meta">{chat.meeting_count} meetings {chat.meeting_count > 0 ? '&bull;' : ''}</div>
                </NavLink>
              </li>
            ))}
            {chats.length === 0 && (
              <li className="text-muted" style={{ padding: '12px 16px', fontSize: '0.875rem' }}>No chats yet.</li>
            )}
          </ul>
        )}
      </div>
      <div className="sidebar-footer">
        <div className="storage-widget">
          <div className="storage-header">
            <span>Storage</span>
            <span>12%</span>
          </div>
          <div className="storage-text">12.4 GB / 100 GB</div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: '12%' }}></div>
          </div>
        </div>
        <div className="profile-widget">
          <div className="avatar">Y</div>
          <div className="user-name">Demo User</div>
        </div>
      </div>
    </aside>
  );
}
