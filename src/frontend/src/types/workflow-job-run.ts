/**
 * Workflow job run types matching backend models
 */

export interface WorkflowJobRun {
  id: string;
  workflow_installation_id: string;
  run_id: number;
  run_name: string | null;
  life_cycle_state: string | null;
  result_state: string | null;
  state_message: string | null;
  start_time: number | null; // Unix timestamp in milliseconds
  end_time: number | null; // Unix timestamp in milliseconds
  duration_ms: number | null;
  notified_at: string | null; // ISO datetime string
  discovered_at: string; // ISO datetime string
  last_updated_at: string; // ISO datetime string
}

export type JobRunStatus = 'SUCCESS' | 'FAILED' | 'CANCELED' | 'TIMEDOUT' | 'RUNNING' | 'PENDING' | 'UNKNOWN';

export function getJobRunStatus(run: WorkflowJobRun): JobRunStatus {
  if (!run.result_state) {
    if (run.life_cycle_state === 'RUNNING') return 'RUNNING';
    if (run.life_cycle_state === 'PENDING') return 'PENDING';
    return 'UNKNOWN';
  }
  return run.result_state.toUpperCase() as JobRunStatus;
}

export function getStatusColor(status: JobRunStatus): string {
  switch (status) {
    case 'SUCCESS':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'FAILED':
      return 'text-red-600 bg-red-50 border-red-200';
    case 'CANCELED':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'TIMEDOUT':
      return 'text-orange-600 bg-orange-50 border-orange-200';
    case 'RUNNING':
      return 'text-blue-600 bg-blue-50 border-blue-200';
    case 'PENDING':
      return 'text-gray-600 bg-gray-50 border-gray-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

export function formatDuration(durationMs: number | null): string {
  if (!durationMs) return '-';

  const seconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}
