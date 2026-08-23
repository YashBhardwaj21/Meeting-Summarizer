import { useState, useEffect } from 'react';
import { jobsApi } from '../api/jobs';
import type { ChatMessage } from '../types/chat';
import type { Job } from '../types/job';

export function useMeetingJobStatuses(messages: ChatMessage[]) {
  const [jobs, setJobs] = useState<Record<string, Job>>({});

  useEffect(() => {
    const activeMeetingMessages = messages.filter(
      (m) => m.message_type === 'meeting' && m.meeting_id
    );

    if (activeMeetingMessages.length === 0) return;

    let timeoutId: number;

    const poll = async () => {
      try {
        const newJobs: Record<string, Job> = { ...jobs };
        let hasPendingJobs = false;

        for (const msg of activeMeetingMessages) {
          if (!msg.meeting_id) continue;
          
          const currentJob = jobs[msg.meeting_id];
          
          // Don't poll if already completed, failed, or cancelled
          if (currentJob && ['completed', 'failed', 'cancelled'].includes(currentJob.status)) {
            continue;
          }

          try {
            const job = await jobsApi.getByMeetingId(msg.meeting_id);
            newJobs[msg.meeting_id] = job;
            if (['queued', 'processing'].includes(job.status)) {
              hasPendingJobs = true;
            }
          } catch (e) {
            console.error(`Failed to fetch job for meeting ${msg.meeting_id}`, e);
          }
        }

        setJobs(newJobs);

        if (hasPendingJobs) {
          timeoutId = window.setTimeout(poll, 3000); // Centralized 3-second poll
        }
      } catch (err) {
        console.error('Centralized polling error', err);
        timeoutId = window.setTimeout(poll, 5000);
      }
    };

    poll();

    return () => {
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [messages]); // Re-run when messages change to pick up new meeting messages

  return jobs;
}
