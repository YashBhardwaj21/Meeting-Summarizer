import React from 'react';

export function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar-search">
        <span className="search-icon">⌕</span>
        <input type="text" placeholder="Search meetings..." />
      </div>
    </header>
  );
}
