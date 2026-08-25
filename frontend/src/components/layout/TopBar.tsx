import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useChats } from '../../hooks/useChats';

export function TopBar() {
  const [query, setQuery] = useState('');
  const { chats } = useChats();
  const navigate = useNavigate();

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && query.trim()) {
      const q = query.toLowerCase();
      const match = chats.find(c => c.title?.toLowerCase().includes(q));
      if (match) {
        navigate(`/chats/${match.id}`);
        setQuery('');
      } else {
        alert(`No workspace found matching "${query}"`);
      }
    }
  };

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div className="topbar-search">
          <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="text" 
            placeholder="Search meetings..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleSearch}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <img src="/logo.png" alt="Profile" style={{ height: '36px', width: '36px', borderRadius: '50%', objectFit: 'cover' }} />
        </div>
      </div>
    </header>
  );
}
