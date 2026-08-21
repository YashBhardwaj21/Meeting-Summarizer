import { useState, useEffect } from 'react';
import { jobsApi } from '../api/jobs';
import type { Job } from '../types/job';

export function useJobPolling(jobId: string | undefined, onComplete?: () => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let timeoutId: number;

    const poll = async () => {
      try {
        const currentJob = await jobsApi.get(jobId);
        setJob(currentJob);

        if (currentJob.status === 'complete') {
          if (onComplete) onComplete();
          return; // Stop polling
        }
        
        if (currentJob.status === 'failed') {
          return; // Stop polling
        }

        // Poll again in 3 seconds
        timeoutId = window.setTimeout(poll, 3000);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch job status'));
        // If it's a 404 or something, we might want to stop, but for now we'll just stop
      }
    };

    poll();

    return () => {
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [jobId, onComplete]);

  return { job, error };
}
