import React, { useEffect } from 'react';
import { NavLink, useParams, useNavigate } from 'react-router';
import { useChats } from '../../hooks/useChats';
import { useStorage } from '../../hooks/useStorage';
import './layout.css';

export function Sidebar() {
  const { chats, loading, refetch } = useChats();
  const { chatId } = useParams();
  const navigate = useNavigate();
  const { usedBytes, quotaBytes, usedPercent, loading: storageLoading } = useStorage(chatId);

  const handleDelete = async (e: React.MouseEvent, id: string, title: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (window.confirm(`Are you sure you want to delete workspace "${title || 'Untitled Workspace'}"?\n\nThis will permanently cancel running jobs and delete all associated meetings, transcripts, and media files.`)) {
      try {
        const { chatsApi } = await import('../../api/chats');
        await chatsApi.delete(id);
        
        // Remove from list and navigate away if active
        refetch();
        if (id === chatId) {
          navigate('/');
        }
      } catch (error) {
        console.error('Failed to delete chat:', error);
        alert('Failed to delete workspace.');
      }
    }
  };

  useEffect(() => {
    if (chatId) {
      refetch();
    }
  }, [chatId, refetch]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="logo">[M] MeetSum</h1>
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
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <div>
                    <div className="chat-name">{chat.title || 'Untitled Workspace'}</div>
                    <div className="chat-meta">{chat.meeting_count} meetings {chat.meeting_count > 0 ? <span>&bull;</span> : ''}</div>
                  </div>
                  <button 
                    onClick={(e) => handleDelete(e, chat.id, chat.title)}
                    className="delete-btn"
                    title="Delete workspace"
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                  >
                    ×
                  </button>
                </NavLink>
              </li>
            ))}
            {chats.length === 0 && (
              <li className="text-muted" style={{ padding: '12px 16px', fontSize: '0.875rem' }}>No chats found.</li>
            )}
          </ul>
        )}
      </div>
      <div className="sidebar-footer">
        <div className="storage-widget">
          <div className="storage-header">
            <span>Storage</span>
            <span>{!chatId ? '—' : storageLoading ? '--' : `${usedPercent}%`}</span>
          </div>
          <div className="storage-text">
            {!chatId ? '—' : storageLoading ? 'Loading...' : `${formatBytes(usedBytes)} / ${formatBytes(quotaBytes)}`}
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${!chatId || storageLoading ? 0 : usedPercent}%` }}></div>
          </div>
        </div>
        <div className="profile-widget">
          <div className="avatar" style={{ backgroundColor: 'var(--color-primary-hover)' }}>W</div>
          <div className="user-name">Local Workspace</div>
        </div>
      </div>
    </aside>
  );
}
