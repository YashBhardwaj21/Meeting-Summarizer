import React from 'react';
import './layout.css';

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="logo">[M] MeetSum</h1>
      </div>
      <div className="sidebar-actions">
        <button className="btn-new-chat">+ New Chat</button>
      </div>
      <div className="sidebar-search">
        <input type="text" placeholder="Search chats..." />
      </div>
      <div className="sidebar-nav">
        <h2 className="nav-heading">CHATS</h2>
        <ul className="chat-list">
          <li className="chat-item active">
            <div className="chat-name">Product Team</div>
            <div className="chat-meta">4 meetings &bull;</div>
          </li>
          <li className="chat-item">
            <div className="chat-name">Design Sync</div>
            <div className="chat-meta">12 meetings</div>
          </li>
        </ul>
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
