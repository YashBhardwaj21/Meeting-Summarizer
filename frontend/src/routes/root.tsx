import React from 'react';
import { MeetingComposer } from '../components/composer/MeetingComposer';
import '../components/layout/layout.css';

export function RootRoute() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 24px' }}>
      <div style={{ width: '100%', maxWidth: '800px', textAlign: 'center', marginBottom: '24px' }}>
        <h2 style={{ marginBottom: '8px', color: 'var(--color-text-primary)' }}>Start a meeting workspace</h2>
        <p style={{ color: 'var(--color-text-muted)' }}>Upload an audio or video file to generate a transcript and summary.</p>
      </div>
      <MeetingComposer />
    </div>
  );
}

