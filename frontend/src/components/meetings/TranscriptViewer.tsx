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
  const isReady = status === 'ready';
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

  const groupedSegments = React.useMemo(() => {
    const groups: { id: string; speaker: string; startTime: number; text: string }[] = [];
    let currentGroup: any = null;

    for (const segment of segments) {
      let rawSpeaker = segment.speaker || 'SPEAKER_00';
      // Normalize SPEAKER_00 -> Speaker 1
      const match = rawSpeaker.match(/SPEAKER_(\d+)/i) || rawSpeaker.match(/speaker_(\d+)/i);
      let displaySpeaker = rawSpeaker;
      if (match) {
        displaySpeaker = `Speaker ${parseInt(match[1], 10) + 1}`;
      }

      if (currentGroup && currentGroup.speaker === displaySpeaker) {
        currentGroup.text += ' ' + segment.text;
      } else {
        if (currentGroup) groups.push(currentGroup);
        currentGroup = {
          id: segment.id,
          speaker: displaySpeaker,
          startTime: segment.start_time,
          text: segment.text
        };
      }
    }
    if (currentGroup) groups.push(currentGroup);
    return groups;
  }, [segments]);

  return (
    <div className="transcript-container">
      <div className="transcript-header" style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Transcript ({total} segments)</h3>
      </div>
      
      <div className="transcript-segments" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {groupedSegments.map((group) => (
          <div key={group.id} className="transcript-segment-group" style={{ display: 'flex', gap: '16px' }}>
            <div className="segment-meta" style={{ width: '80px', flexShrink: 0 }}>
              <div className="segment-speaker" style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--color-text)' }}>
                {group.speaker}
              </div>
              <div className="segment-time" style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                {formatTime(group.startTime)}
              </div>
            </div>
            <div className="segment-text" style={{ flex: 1, fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--color-text)' }}>
              {group.text}
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
