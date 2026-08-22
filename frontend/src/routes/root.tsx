import React from 'react';

import '../components/layout/layout.css';

export function RootRoute() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 24px' }}>
      <div style={{ width: '100%', maxWidth: '800px', textAlign: 'center', marginBottom: '24px' }}>
        <h2 style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>Welcome to MeetSum</h2>
        <p style={{ color: 'var(--color-text-muted)' }}>Click "+ New chat" in the sidebar to start a new workspace.</p>
      </div>
    </div>
  );
}

