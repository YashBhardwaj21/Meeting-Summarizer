import React, { useEffect, useState } from 'react';
import { NavLink, useParams, useNavigate } from 'react-router';
import { useChats } from '../../hooks/useChats';
import { useStorage } from '../../hooks/useStorage';
import type { Chat } from '../../types/chat';
import './layout.css';

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
      <div className="sidebar-header">
        <h1 className="logo">[M] MeetSum</h1>
      </div>
      <div className="sidebar-nav">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingRight: '16px' }}>
          <h2 className="nav-heading">CHATS</h2>
          <button 
            onClick={handleCreateChat} 
            disabled={creating}
            className="btn-primary"
            style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto', marginBottom: '8px' }}
          >
            {creating ? '...' : '+ New'}
          </button>
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
                    onClick={(e) => handleDeleteClick(e, chat.id, chat.title)}
                    className="delete-btn"
                    title="Delete workspace"
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                  >
                    ×
                  </button>
                </NavLink>
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
