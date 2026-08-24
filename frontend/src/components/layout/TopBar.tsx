import React from 'react';

export function TopBar() {
  return (
    <header className="topbar">
      <div className="topbar-logo-mobile" style={{ display: 'flex', alignItems: 'center' }}>
        <img src="/logo.png" alt="Logo" style={{ height: '48px', width: '48px' }} />
      </div>
    </header>
  );
}
