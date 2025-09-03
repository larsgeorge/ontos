from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import configparser
import time
import threading

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs
from databricks.sdk.service.jobs import RunState, RunResultState
from sqlalchemy.orm import Session

from src.common.logging import get_logger

logger = get_logger(__name__)


class JobsManager:
    def __init__(self, db: Session, ws_client: WorkspaceClient, *, workflows_root: Optional[Path] = None, notifications_manager=None):
        self._db = db
        self._client = ws_client
        self._workflows_root = workflows_root or Path(__file__).parent.parent / "workflows"
        self._notifications_manager = notifications_manager
        self._running_jobs: Dict[int, str] = {}  # run_id -> notification_id

    def list_available_workflows(self) -> List[Dict[str, str]]:
        root = self._workflows_root
        if not root.exists():
            return []
        items: List[Dict[str, str]] = []
        for d in root.iterdir():
            if not d.is_dir():
                continue
            yaml_file = d / f"{d.name}.yaml"
            if not yaml_file.exists():
                continue
            name = d.name
            description = ""
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f) or {}
                    if isinstance(data, dict):
                        name = str(data.get("name", name))
                        if data.get("description"):
                            description = str(data.get("description"))
            except Exception:
                name = d.name
            items.append({"id": d.name, "name": name, "description": description})
        return items

    def install_workflow(self, workflow_id: str, *, job_cluster_id: Optional[str] = None) -> int:
        wf_def = self._get_workflow_definition(workflow_id, job_cluster_id=job_cluster_id)
        
        # Build job settings with additional configuration options
        job_settings = jobs.JobSettings(
            name=wf_def.get('name', workflow_id),
            tasks=self._build_tasks_from_definition(wf_def)
        )
        
        # Add optional job configuration from YAML
        if 'schedule' in wf_def:
            schedule_config = wf_def['schedule']
            if isinstance(schedule_config, dict):
                cron_schedule = jobs.CronSchedule(
                    quartz_cron_expression=schedule_config.get('quartz_cron_expression'),
                    timezone_id=schedule_config.get('timezone_id', 'UTC'),
                    pause_status=jobs.PauseStatus(schedule_config.get('pause_status', 'UNPAUSED'))
                )
                job_settings.schedule = cron_schedule
        
        if 'continuous' in wf_def and wf_def['continuous']:
            job_settings.continuous = jobs.Continuous(pause_status=jobs.PauseStatus.UNPAUSED)
        
        if 'parameters' in wf_def:
            job_settings.parameters = wf_def['parameters']
        
        if 'tags' in wf_def:
            job_settings.tags = wf_def['tags']
        
        if 'timeout_seconds' in wf_def:
            job_settings.timeout_seconds = int(wf_def['timeout_seconds'])
        
        if 'max_concurrent_runs' in wf_def:
            job_settings.max_concurrent_runs = int(wf_def['max_concurrent_runs'])
        
        if 'email_notifications' in wf_def:
            email_config = wf_def['email_notifications']
            if isinstance(email_config, dict):
                job_settings.email_notifications = jobs.JobEmailNotifications(
                    on_start=email_config.get('on_start', []),
                    on_success=email_config.get('on_success', []),
                    on_failure=email_config.get('on_failure', []),
                    no_alert_for_skipped_runs=email_config.get('no_alert_for_skipped_runs', False)
                )
        
        created = self._client.jobs.create(**job_settings.as_dict())
        return int(created.job_id)

    def update_workflow(self, workflow_id: str, job_id: int, *, job_cluster_id: Optional[str] = None) -> None:
        wf_def = self._get_workflow_definition(workflow_id, job_cluster_id=job_cluster_id)
        
        # Build job settings with additional configuration options
        job_settings = jobs.JobSettings(
            name=wf_def.get('name'),
            tasks=self._build_tasks_from_definition(wf_def)
        )
        
        # Add optional job configuration from YAML
        if 'schedule' in wf_def:
            schedule_config = wf_def['schedule']
            if isinstance(schedule_config, dict):
                cron_schedule = jobs.CronSchedule(
                    quartz_cron_expression=schedule_config.get('quartz_cron_expression'),
                    timezone_id=schedule_config.get('timezone_id', 'UTC'),
                    pause_status=jobs.PauseStatus(schedule_config.get('pause_status', 'UNPAUSED'))
                )
                job_settings.schedule = cron_schedule
        
        if 'continuous' in wf_def and wf_def['continuous']:
            job_settings.continuous = jobs.Continuous(pause_status=jobs.PauseStatus.UNPAUSED)
        
        if 'parameters' in wf_def:
            job_settings.parameters = wf_def['parameters']
        
        if 'tags' in wf_def:
            job_settings.tags = wf_def['tags']
        
        if 'timeout_seconds' in wf_def:
            job_settings.timeout_seconds = int(wf_def['timeout_seconds'])
        
        if 'max_concurrent_runs' in wf_def:
            job_settings.max_concurrent_runs = int(wf_def['max_concurrent_runs'])
        
        if 'email_notifications' in wf_def:
            email_config = wf_def['email_notifications']
            if isinstance(email_config, dict):
                job_settings.email_notifications = jobs.JobEmailNotifications(
                    on_start=email_config.get('on_start', []),
                    on_success=email_config.get('on_success', []),
                    on_failure=email_config.get('on_failure', []),
                    no_alert_for_skipped_runs=email_config.get('no_alert_for_skipped_runs', False)
                )
        
        self._client.jobs.update(job_id=job_id, new_settings=job_settings)

    def remove_workflow(self, job_id: int) -> None:
        self._client.jobs.delete(job_id=job_id)

    def run_job(self, job_id: int, job_name: Optional[str] = None) -> int:
        """Run a job and create a progress notification."""
        run = self._client.jobs.run_now(job_id=job_id)
        run_id = int(run.run_id)
        
        if self._notifications_manager:
            # Get job name if not provided
            if not job_name:
                job = self._client.jobs.get(job_id=job_id)
                job_name = job.settings.name if job.settings else f"Job {job_id}"
            
            # Create progress notification for admin users
            notification_id = self._create_job_progress_notification(job_name, run_id)
            self._running_jobs[run_id] = notification_id
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_job_progress,
                args=(run_id, job_name, notification_id),
                daemon=True
            )
            monitor_thread.start()
        
        return run_id

    def find_job_by_name(self, job_name: str) -> Optional[jobs.Job]:
        all_jobs = self._client.jobs.list()
        return next((job for job in all_jobs if job.settings.name == job_name), None)

    # --- internals ---
    def _get_workflow_definition(self, workflow_id: str, *, job_cluster_id: Optional[str]) -> Dict[str, Any]:
        base = self._workflows_root / workflow_id
        if not base.exists():
            raise ValueError(f"Workflow not found: {workflow_id}")
        yaml_path = base / f"{workflow_id}.yaml"
        ini_path = base / "job.ini"
        wf: Dict[str, Any]
        if yaml_path.exists():
            with open(yaml_path) as f:
                wf = yaml.safe_load(f) or {}
        elif ini_path.exists():
            config = configparser.ConfigParser()
            config.read(ini_path)
            wf = {
                "name": config.get("job", "name", fallback=workflow_id),
                "format": config.get("job", "format", fallback="MULTI_TASK"),
                "tasks": []
            }
            for section in config.sections():
                if not section.startswith("task:"):
                    continue
                tkey = section.split(":", 1)[1]
                task: Dict[str, Any] = {"task_key": tkey}
                nb = config.get(section, "notebook_path", fallback=None)
                if nb:
                    task["notebook_task"] = {"notebook_path": nb}
                wheel = config.get(section, "python_wheel_task", fallback=None)
                if wheel:
                    try:
                        task["python_wheel_task"] = json.loads(wheel)
                    except Exception:
                        logger.warning(f"Invalid python_wheel_task JSON in {ini_path} for {tkey}")
                wf["tasks"].append(task)
        else:
            raise ValueError(f"Workflow definition not found: {yaml_path} or {ini_path}")

        if job_cluster_id and isinstance(wf.get("tasks"), list):
            for t in wf["tasks"]:
                if "existing_cluster_id" not in t and "new_cluster" not in t:
                    t["existing_cluster_id"] = job_cluster_id
        return wf

    def _build_tasks_from_definition(self, wf: Dict[str, Any]) -> List[jobs.Task]:
        tasks: List[jobs.Task] = []
        for t in wf.get('tasks', []) or []:
            if not isinstance(t, dict):
                continue
            kwargs: Dict[str, Any] = {}
            if 'task_key' in t:
                kwargs['task_key'] = t['task_key']
            if 'existing_cluster_id' in t:
                kwargs['existing_cluster_id'] = t['existing_cluster_id']
            if 'notebook_task' in t and isinstance(t['notebook_task'], dict):
                kwargs['notebook_task'] = jobs.NotebookTask(**t['notebook_task'])
            if 'python_wheel_task' in t and isinstance(t['python_wheel_task'], dict):
                kwargs['python_wheel_task'] = jobs.PythonWheelTask(**t['python_wheel_task'])
            tasks.append(jobs.Task(**kwargs))
        return tasks

    def _create_job_progress_notification(self, job_name: str, run_id: int) -> str:
        """Create a progress notification for job execution."""
        from src.models.notifications import Notification, NotificationType
        
        notification = Notification(
            id=f"job-progress-{run_id}-{int(time.time())}",
            type=NotificationType.JOB_PROGRESS,
            title=f"Job Running: {job_name}",
            message=f"Job '{job_name}' (Run ID: {run_id}) is currently running...",
            data={
                "job_name": job_name,
                "run_id": run_id,
                "progress": 0,
                "status": "RUNNING"
            },
            target_roles=["Admin"],  # Only notify admins
            created_at=datetime.utcnow()
        )
        
        # Create notification via notifications manager
        self._notifications_manager.create_notification(notification, db=self._db)
        return notification.id

    def _monitor_job_progress(self, run_id: int, job_name: str, notification_id: str):
        """Monitor job progress and update notification."""
        try:
            while True:
                try:
                    run = self._client.jobs.get_run(run_id=run_id)
                    state = run.state
                    
                    if not state:
                        time.sleep(5)
                        continue
                    
                    # Update notification based on job state
                    if state.life_cycle_state in [RunState.RUNNING, RunState.PENDING]:
                        # Job is still running, update progress
                        progress_data = {
                            "job_name": job_name,
                            "run_id": run_id,
                            "progress": 50 if state.life_cycle_state == RunState.RUNNING else 25,
                            "status": state.life_cycle_state.value
                        }
                        
                        self._update_job_notification(
                            notification_id,
                            f"Job Running: {job_name}",
                            f"Job '{job_name}' (Run ID: {run_id}) is {state.life_cycle_state.value.lower()}...",
                            progress_data
                        )
                        
                        time.sleep(10)  # Check every 10 seconds
                        
                    elif state.life_cycle_state in [RunState.TERMINATED, RunState.SKIPPED, RunState.INTERNAL_ERROR]:
                        # Job completed, update final notification
                        is_success = (
                            state.life_cycle_state == RunState.TERMINATED and 
                            state.result_state == RunResultState.SUCCESS
                        )
                        
                        final_data = {
                            "job_name": job_name,
                            "run_id": run_id,
                            "progress": 100,
                            "status": "SUCCESS" if is_success else "FAILED",
                            "result_state": state.result_state.value if state.result_state else None
                        }
                        
                        title = f"Job {'Completed' if is_success else 'Failed'}: {job_name}"
                        message = f"Job '{job_name}' (Run ID: {run_id}) has {'completed successfully' if is_success else 'failed'}."
                        
                        self._update_job_notification(notification_id, title, message, final_data)
                        
                        # Remove from running jobs tracking
                        self._running_jobs.pop(run_id, None)
                        break
                        
                except Exception as e:
                    logger.error(f"Error monitoring job {run_id}: {e}")
                    time.sleep(30)  # Wait longer on error
                    
        except Exception as e:
            logger.error(f"Failed to monitor job {run_id}: {e}")
            # Clean up on error
            self._running_jobs.pop(run_id, None)

    def _update_job_notification(self, notification_id: str, title: str, message: str, data: Dict[str, Any]):
        """Update an existing job progress notification."""
        try:
            from src.models.notifications import NotificationUpdate
            
            update = NotificationUpdate(
                title=title,
                message=message,
                data=data,
                updated_at=datetime.utcnow()
            )
            
            self._notifications_manager.update_notification(notification_id, update, db=self._db)
            
        except Exception as e:
            logger.error(f"Failed to update notification {notification_id}: {e}")

    def get_job_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get the current status of a running job."""
        try:
            run = self._client.jobs.get_run(run_id=run_id)
            if not run.state:
                return None
                
            return {
                "run_id": run_id,
                "job_id": run.job_id,
                "life_cycle_state": run.state.life_cycle_state.value,
                "result_state": run.state.result_state.value if run.state.result_state else None,
                "start_time": run.start_time,
                "end_time": run.end_time
            }
        except Exception as e:
            logger.error(f"Failed to get job status for run {run_id}: {e}")
            return None


