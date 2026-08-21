import React from 'react';
import type { Meeting } from '../../types/meeting';
import { MeetingCard } from './MeetingCard';
import { EmptyState } from '../ui/EmptyState';
import { SkeletonText } from '../ui/Skeleton';

interface MeetingListProps {
  meetings: Meeting[];
  loading: boolean;
}

export function MeetingList({ meetings, loading }: MeetingListProps) {
  if (loading && meetings.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <SkeletonText lines={2} />
        <SkeletonText lines={2} />
        <SkeletonText lines={2} />
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <EmptyState 
        icon="🗂️"
        title="No meetings yet"
        description="Upload your first meeting media to begin processing."
      />
    );
  }

  return (
    <div className="meeting-list">
      {meetings.map(meeting => (
        <MeetingCard key={meeting.id} meeting={meeting} />
      ))}
    </div>
  );
}
