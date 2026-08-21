import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MeetingList } from '../MeetingList';
import { BrowserRouter } from 'react-router';
import type { Meeting } from '../../../types/meeting';

const mockMeetings: Meeting[] = [
  {
    id: 'm1',
    chat_id: 'c1',
    file_id: 'f1',
    title: 'Weekly Sync',
    status: 'ready',
    duration_seconds: 3600,
    created_at: '2026-08-20T10:00:00Z',
  },
  {
    id: 'm2',
    chat_id: 'c1',
    file_id: 'f2',
    title: 'Project Kickoff',
    status: 'processing',
    duration_seconds: null,
    created_at: '2026-08-21T14:30:00Z',
  }
];

describe('MeetingList Component', () => {
  it('renders loading skeletons when loading', () => {
    const { container } = render(
      <BrowserRouter>
        <MeetingList meetings={[]} loading={true} />
      </BrowserRouter>
    );
    expect(container.getElementsByClassName('skeleton-text-group').length).toBeGreaterThan(0);
  });

  it('renders empty state when no meetings exist', () => {
    render(
      <BrowserRouter>
        <MeetingList meetings={[]} loading={false} />
      </BrowserRouter>
    );
    expect(screen.getByText('No meetings yet')).toBeDefined();
    expect(screen.getByText(/Upload your first meeting/i)).toBeDefined();
  });

  it('renders a list of meetings', () => {
    render(
      <BrowserRouter>
        <MeetingList meetings={mockMeetings} loading={false} />
      </BrowserRouter>
    );
    expect(screen.getByText('Weekly Sync')).toBeDefined();
    expect(screen.getByText('Project Kickoff')).toBeDefined();
    expect(screen.getByText('READY')).toBeDefined();
    expect(screen.getByText('PROCESSING')).toBeDefined();
  });
});
