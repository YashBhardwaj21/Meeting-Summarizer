import React from 'react';
import { EmptyState } from '../components/ui/EmptyState';

export function RootRoute() {
  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <EmptyState 
        icon="👋" 
        title="Welcome to MeetSum" 
        description="Select a chat from the sidebar or create a new one to get started." 
      />
    </div>
  );
}
