export type JobRunSimpleResult = 'SUCCESS' | 'FAILED' | 'CANCELED' | 'TIMEDOUT' | 'PENDING' | null;

export type PauseState = 'PAUSED' | 'UNPAUSED' | 'NONE' | null;

export interface WorkflowStatus {
  workflow_id: string;
  installed: boolean;
  job_id?: number | null;
  is_running: boolean;
  current_run_id?: number | null;
  last_result?: JobRunSimpleResult;
  last_ended_at?: number | null;
  pause_status?: PauseState;
  supports_pause: boolean;
}


