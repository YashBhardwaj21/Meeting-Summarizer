import React, { useEffect, useState } from 'react';
import { NavLink, useParams, useNavigate } from 'react-router';
import { useChats } from '../../hooks/useChats';
import { useStorage } from '../../hooks/useStorage';
import type { Chat } from '../../types/chat';
import './layout.css';

function ChatItem({ chat, isActive, onDeleteClick, onRename }: { chat: Chat, isActive: boolean, onDeleteClick: (e: React.MouseEvent, id: string, title: string | null) => void, onRename: (id: string, title: string) => Promise<void> }) {
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(chat.title || 'Untitled Workspace');
  const [saving, setSaving] = useState(false);

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setTitle(chat.title || 'Untitled Workspace');
    setIsEditing(true);
  };

  const handleSave = async () => {
    const trimmed = title.trim();
    if (!trimmed || trimmed === (chat.title || 'Untitled Workspace')) {
      setTitle(chat.title || 'Untitled Workspace');
      setIsEditing(false);
      return;
    }

    try {
      setSaving(true);
      await onRename(chat.id, trimmed);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to rename chat', error);
      setTitle(chat.title || 'Untitled Workspace');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void handleSave();
    }
    if (e.key === 'Escape') {
      setTitle(chat.title || 'Untitled Workspace');
      setIsEditing(false);
    }
  };

  return (
    <NavLink 
      to={`/chats/${chat.id}`} 
      className={`chat-item ${isActive ? 'active' : ''}`}
      style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}
    >
      <div style={{ flexShrink: 0, color: isActive ? 'var(--color-text)' : 'var(--color-text-muted)', display: 'flex', alignItems: 'center' }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <div style={{ flex: 1, minWidth: 0, marginRight: '4px' }}>
        {isEditing ? (
          <input
            autoFocus
            value={title}
            disabled={saving}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={() => void handleSave()}
            onKeyDown={handleKeyDown}
            className="chat-title-input"
            onClick={(e) => e.preventDefault()}
          />
        ) : (
          <div 
            className="chat-name chat-title-editable" 
            onDoubleClick={handleDoubleClick}
            title="Double-click to rename"
          >
            {title}
          </div>
        )}
      </div>
      <button 
        onClick={(e) => onDeleteClick(e, chat.id, chat.title)}
        className="delete-btn"
        title="Delete workspace"
        style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="1.5"></circle>
          <circle cx="19" cy="12" r="1.5"></circle>
          <circle cx="5" cy="12" r="1.5"></circle>
        </svg>
      </button>
    </NavLink>
  );
}

export function Sidebar() {
  const { chats, loading, creating, refetch, createChat } = useChats();
  const [localChats, setLocalChats] = useState<Chat[]>([]);
  const { chatId } = useParams();
  const navigate = useNavigate();
  const { usedBytes, quotaBytes, usedPercent, loading: storageLoading } = useStorage(chatId);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<{id: string, title: string | null} | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    setLocalChats(chats);
  }, [chats]);

  const handleDeleteClick = (e: React.MouseEvent, id: string, title: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    setChatToDelete({ id, title });
    setDeleteError(null);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!chatToDelete) return;
    
    setIsDeleting(true);
    setDeleteError(null);
    
    try {
      const { chatsApi } = await import('../../api/chats');
      await chatsApi.delete(chatToDelete.id);
      
      // Optimistic update
      setLocalChats(prev => prev.filter(c => c.id !== chatToDelete.id));
      
      if (chatToDelete.id === chatId) {
        navigate('/');
      }
      
      setDeleteModalOpen(false);
      refetch();
    } catch (error: any) {
      console.error('Failed to delete chat:', error);
      setDeleteError(error?.response?.data?.detail || error.message || 'Failed to delete workspace.');
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteModalOpen(false);
    setChatToDelete(null);
  };

  const handleRenameChat = async (id: string, newTitle: string) => {
    try {
      const { chatsApi } = await import('../../api/chats');
      const updatedChat = await chatsApi.rename(id, newTitle);
      setLocalChats(prev => prev.map(c => c.id === id ? { ...c, title: updatedChat.title } : c));
      refetch();
    } catch (error) {
      throw error;
    }
  };

  const handleCreateChat = async () => {
    setCreateError(null);
    try {
      const newChat = await createChat('Untitled Workspace');
      navigate(`/chats/${newChat.id}`);
    } catch (error: any) {
      console.error('Failed to create chat:', error);
      setCreateError(error?.response?.data?.detail || error.message || 'Failed to create workspace.');
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
      <div className="sidebar-header" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="2" x2="12" y2="6"></line>
          <line x1="12" y1="18" x2="12" y2="22"></line>
          <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
          <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
          <line x1="2" y1="12" x2="6" y2="12"></line>
          <line x1="18" y1="12" x2="22" y2="12"></line>
          <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
          <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
        </svg>
        <h1 className="logo" style={{ margin: 0, letterSpacing: '0.05em' }}>LUMI</h1>
      </div>
      
      <div className="sidebar-actions">
        <button
          onClick={handleCreateChat}
          disabled={creating}
          className="btn-new-chat"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '1rem', color: '#111' }}
        >
          <span style={{ fontSize: '1.4rem', fontWeight: 300 }}>+</span> {creating ? 'Creating...' : 'New Chat'}
        </button>
      </div>

      <div className="sidebar-nav">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: '16px' }}>
          <h2 className="nav-heading" style={{ textTransform: 'uppercase' }}>Meetings</h2>
        </div>
        {createError && (
          <div style={{ color: 'var(--color-danger)', fontSize: '0.75rem', padding: '0 16px 8px' }}>
            {createError}
          </div>
        )}
        {loading ? (
          <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
            <div className="skeleton" style={{ height: '48px', width: '100%' }}></div>
          </div>
        ) : (
          <ul className="chat-list">
            {localChats.map(chat => (
              <li key={chat.id}>
                <ChatItem 
                  chat={chat} 
                  isActive={chat.id === chatId} 
                  onDeleteClick={handleDeleteClick} 
                  onRename={handleRenameChat} 
                />
              </li>
            ))}
            {localChats.length === 0 && (
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
      
      {deleteModalOpen && chatToDelete && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal-content" style={{ backgroundColor: 'var(--color-bg)', padding: '24px', borderRadius: 'var(--radius-sm)', maxWidth: '400px', width: '100%', border: 'var(--border)', boxShadow: '4px 4px 0px var(--color-border)' }}>
            <h3 style={{ marginTop: 0, marginBottom: '16px', color: 'var(--color-text)' }}>Delete Workspace</h3>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '16px', fontSize: '1rem', lineHeight: '1.5' }}>
              Are you sure you want to delete workspace "{chatToDelete.title || 'Untitled Workspace'}"?
            </p>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '24px', fontSize: '0.9rem', lineHeight: '1.5' }}>
              This will permanently cancel running jobs and delete all associated meetings, transcripts, and media files.
            </p>
            {deleteError && (
              <div style={{ color: 'var(--color-red)', marginBottom: '16px', fontSize: '0.9rem', padding: '8px', border: 'var(--border)', backgroundColor: 'rgba(255,0,0,0.1)' }}>
                {deleteError}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button onClick={cancelDelete} disabled={isDeleting} className="btn-secondary" style={{ padding: '8px 16px', border: 'var(--border)', backgroundColor: 'var(--color-surface)', boxShadow: '2px 2px 0px var(--color-border)', cursor: 'pointer', fontWeight: 'bold' }}>Cancel</button>
              <button onClick={confirmDelete} disabled={isDeleting} className="btn-primary" style={{ padding: '8px 16px', border: 'var(--border)', backgroundColor: 'var(--color-red)', color: 'white', boxShadow: '2px 2px 0px var(--color-border)', cursor: 'pointer', fontWeight: 'bold' }}>
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
