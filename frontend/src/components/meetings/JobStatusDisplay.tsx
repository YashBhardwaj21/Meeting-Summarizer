import React from 'react';
import type { Job } from '../../types/job';
import './meetings.css'; // Will add styles there

interface JobStatusProps {
  job: Job;
}

export function JobStatusDisplay({ job }: JobStatusProps) {
  const isFailed = job.status === 'failed';
  const isComplete = job.status === 'completed';
  const inProgress = job.status === 'processing' || job.status === 'queued';

  // Map stages to a friendly display
  const stageDisplay = job.stage ? job.stage.replace(/_/g, ' ') : 'Initializing...';

  const handleCancel = async () => {
    try {
      const { jobsApi } = await import('../../api/jobs');
      await jobsApi.cancel(job.id);
    } catch (e) {
      console.error('Failed to cancel job', e);
      alert('Failed to cancel job');
    }
  };

  return (
    <div className={`job-status-card ${isFailed ? 'failed' : ''} ${isComplete ? 'complete' : ''}`}>
      <div className="job-status-header">
        <h3>Processing Status</h3>
        <span className={`status-badge status-${isFailed ? 'failed' : isComplete ? 'ready' : job.status === 'cancelled' ? 'cancelled' : 'processing'}`}>
          {job.status.replace('_', ' ').toUpperCase()}
        </span>
      </div>
      
      {inProgress && (
        <div className="job-progress" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="spinner"></div>
          <div className="job-stage" style={{ flex: 1 }}>
            {job.status === 'queued' ? 'Waiting for processing worker...' : `Current stage: ${stageDisplay}`}
          </div>
          <button 
            onClick={handleCancel} 
            className="btn-secondary" 
            style={{ padding: '4px 12px', fontSize: '0.875rem' }}
          >
            Cancel
          </button>
        </div>
      )}
      
      {isFailed && (
        <div className="job-error">
          <strong>Processing failed.</strong> {job.error_message || 'An unknown error occurred during processing.'}
        </div>
      )}

      {job.status === 'cancelled' && (
        <div className="job-error" style={{ color: 'var(--text-muted)', backgroundColor: 'var(--color-surface-hover)', borderColor: 'var(--border)' }}>
          Processing was cancelled.
        </div>
      )}

      {isComplete && (
        <div className="job-complete">
          Processing completed successfully. Transcript is ready.
        </div>
      )}
    </div>
  );
}
