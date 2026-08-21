import React from 'react';
import { useTranscripts } from '../../hooks/useTranscripts';

import { SkeletonText } from '../ui/Skeleton';
import { EmptyState } from '../ui/EmptyState';
import { LoadingSpinner } from '../ui/LoadingSpinner';

interface TranscriptViewerProps {
  chatId: string;
  meetingId: string;
  isReady: boolean;
}

function formatTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export function TranscriptViewer({ chatId, meetingId, isReady }: TranscriptViewerProps) {
  const { segments, loading, error, hasMore, loadMore, total } = useTranscripts(chatId, meetingId, isReady);

  if (error) {
    return <div className="upload-error">{error.message}</div>;
  }

  if (loading && segments.length === 0) {
    return (
      <div style={{ marginTop: '24px' }}>
        <SkeletonText lines={4} />
        <div style={{ height: '24px' }}></div>
        <SkeletonText lines={3} />
        <div style={{ height: '24px' }}></div>
        <SkeletonText lines={5} />
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <EmptyState 
        icon="📝" 
        title="No transcript available" 
        description="The transcript could not be generated or is empty." 
      />
    );
  }

  return (
    <div className="transcript-container">
      <div className="transcript-header" style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Transcript ({total} segments)</h3>
      </div>
      
      <div className="transcript-segments" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {segments.map((segment) => (
          <div key={segment.id} className="transcript-segment" style={{ display: 'flex', gap: '16px' }}>
            <div className="segment-meta" style={{ width: '80px', flexShrink: 0 }}>
              <div className="segment-time" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>
                {formatTime(segment.start_time)}
              </div>
              <div className="segment-speaker" style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-primary-hover)' }}>
                {segment.speaker || 'SPEAKER_00'}
              </div>
            </div>
            <div className="segment-text" style={{ flex: 1, backgroundColor: 'var(--color-surface)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: 'var(--border)' }}>
              {segment.text}
            </div>
          </div>
        ))}
      </div>

      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <button 
            className="btn-secondary" 
            onClick={loadMore} 
            disabled={loading}
            style={{ border: 'var(--border)', backgroundColor: 'var(--color-surface)' }}
          >
            {loading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}
