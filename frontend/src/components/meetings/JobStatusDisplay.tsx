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

  return (
    <div className={`job-status-card ${isFailed ? 'failed' : ''} ${isComplete ? 'complete' : ''}`}>
      <div className="job-status-header">
        <h3>Processing Status</h3>
        <span className={`status-badge status-${isFailed ? 'failed' : isComplete ? 'ready' : 'processing'}`}>
          {job.status.replace('_', ' ').toUpperCase()}
        </span>
      </div>
      
      {inProgress && (
        <div className="job-progress">
          <div className="spinner"></div>
          <div className="job-stage">Current stage: <strong>{stageDisplay}</strong></div>
        </div>
      )}
      
      {isFailed && (
        <div className="job-error">
          <strong>Error:</strong> {job.error_message || 'An unknown error occurred during processing.'}
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
