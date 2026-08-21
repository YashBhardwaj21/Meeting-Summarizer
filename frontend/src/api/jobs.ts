import { api } from './client';
import type { Job } from '../types/job';

export const jobsApi = {
  get: (jobId: string) => api.get<Job>(`/jobs/${jobId}`),
  cancel: (jobId: string) => api.post<Job>(`/jobs/${jobId}/cancel`),
};
