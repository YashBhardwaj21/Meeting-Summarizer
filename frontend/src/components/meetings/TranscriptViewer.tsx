import React from 'react';
import { useTranscripts } from '../../hooks/useTranscripts';

import { SkeletonText } from '../ui/Skeleton';
import { EmptyState } from '../ui/EmptyState';

interface TranscriptViewerProps {
  chatId: string;
  meetingId: string;
  status: string;
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

export function TranscriptViewer({ chatId, meetingId, status }: TranscriptViewerProps) {
  const isReady = status === 'completed' || status === 'ready';
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
    if (status === 'pending' || status === 'queued' || status === 'processing') {
      return null;
    }
    
    return (
      <EmptyState 
        icon="📝" 
        title="No transcript available" 
        description="The transcript could not be generated or is empty." 
      />
    );
  }

  return (
    <div className="transcript-container neo-panel" style={{ maxHeight: '480px', overflowY: 'auto', padding: '16px', border: 'var(--border)', backgroundColor: 'var(--color-surface)', position: 'relative' }}>
      <div className="transcript-segments" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {segments.map((segment) => {
          let rawSpeaker = segment.speaker || 'Unknown';
          const match = rawSpeaker.match(/SPEAKER_(\d+)/i) || rawSpeaker.match(/speaker_(\d+)/i);
          let displaySpeaker = rawSpeaker;
          if (match) {
            displaySpeaker = `Speaker ${parseInt(match[1], 10) + 1}`;
          }

          return (
            <div key={segment.id} className="transcript-segment-item" style={{ display: 'flex', gap: '16px' }}>
              <div className="segment-meta" style={{ width: '80px', flexShrink: 0 }}>
                <div className="segment-speaker" style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text)' }}>
                  {displaySpeaker}
                </div>
                <div className="segment-time" style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                  {formatTime(segment.start_time)}
                </div>
              </div>
              <div className="segment-text" style={{ flex: 1, fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--color-text)' }}>
                {segment.text}
              </div>
            </div>
          );
        })}
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
