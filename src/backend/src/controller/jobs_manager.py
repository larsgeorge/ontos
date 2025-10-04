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
from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState
from sqlalchemy.orm import Session

from src.common.logging import get_logger
from src.repositories.workflow_installations_repository import workflow_installation_repo
from src.repositories.workflow_job_runs_repository import workflow_job_run_repo
from src.models.workflow_installations import WorkflowInstallation

logger = get_logger(__name__)


class JobsManager:
    def __init__(self, db: Session, ws_client: WorkspaceClient, *, workflows_root: Optional[Path] = None, notifications_manager=None, settings=None):
        self._db = db
        self._client = ws_client
        self._workflows_root = workflows_root or Path(__file__).parent.parent / "workflows"
        self._notifications_manager = notifications_manager
        self._settings = settings
        self._running_jobs: Dict[int, str] = {}  # run_id -> notification_id
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()

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

        # Build job settings kwargs from workflow definition
        tasks = self._build_tasks_from_definition(wf_def)
        job_settings_kwargs = {
            'name': wf_def.get('name', workflow_id),
            'tasks': tasks  # Keep as Task objects
        }

        # Check if any tasks need serverless (no cluster_id specified)
        # If so, add default environment for serverless compute
        has_serverless_tasks = any(
            not hasattr(task, 'existing_cluster_id') or task.existing_cluster_id is None
            for task in tasks
        )
        if has_serverless_tasks and 'environments' not in wf_def:
            from databricks.sdk.service import compute

            # Add default serverless environment
            job_settings_kwargs['environments'] = [
                jobs.JobEnvironment(
                    environment_key='default',
                    spec=compute.Environment(
                        client='1'  # Use default Databricks runtime
                    )
                )
            ]
            # Set environment_key on tasks that don't have a cluster
            for task in tasks:
                if not hasattr(task, 'existing_cluster_id') or task.existing_cluster_id is None:
                    task.environment_key = 'default'

        # Add optional job configuration from YAML
        if 'schedule' in wf_def:
            schedule_config = wf_def['schedule']
            if isinstance(schedule_config, dict):
                job_settings_kwargs['schedule'] = jobs.CronSchedule(
                    quartz_cron_expression=schedule_config.get('quartz_cron_expression'),
                    timezone_id=schedule_config.get('timezone_id', 'UTC'),
                    pause_status=jobs.PauseStatus(schedule_config.get('pause_status', 'UNPAUSED'))
                )

        if 'continuous' in wf_def and wf_def['continuous']:
            job_settings_kwargs['continuous'] = jobs.Continuous(pause_status=jobs.PauseStatus.UNPAUSED)

        if 'parameters' in wf_def:
            job_settings_kwargs['parameters'] = wf_def['parameters']

        if 'tags' in wf_def:
            job_settings_kwargs['tags'] = wf_def['tags']

        if 'timeout_seconds' in wf_def:
            job_settings_kwargs['timeout_seconds'] = int(wf_def['timeout_seconds'])

        if 'max_concurrent_runs' in wf_def:
            job_settings_kwargs['max_concurrent_runs'] = int(wf_def['max_concurrent_runs'])

        if 'email_notifications' in wf_def:
            email_config = wf_def['email_notifications']
            if isinstance(email_config, dict):
                job_settings_kwargs['email_notifications'] = jobs.JobEmailNotifications(
                    on_start=email_config.get('on_start', []),
                    on_success=email_config.get('on_success', []),
                    on_failure=email_config.get('on_failure', []),
                    no_alert_for_skipped_runs=email_config.get('no_alert_for_skipped_runs', False)
                )

        # Create the job directly with kwargs (no JobSettings intermediate object needed)
        created = self._client.jobs.create(**job_settings_kwargs)
        job_id = int(created.job_id)

        # Persist installation to database
        try:
            # Get workspace_id from settings if available
            workspace_id = None
            if self._settings and hasattr(self._settings, 'DATABRICKS_HOST'):
                # Use host as workspace identifier since DATABRICKS_WORKSPACE_ID doesn't exist
                workspace_id = self._settings.DATABRICKS_HOST

            installation = WorkflowInstallation(
                workflow_id=workflow_id,
                name=wf_def.get('name', workflow_id),
                job_id=job_id,
                workspace_id=workspace_id,
                status='installed',
                installed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            workflow_installation_repo.create(self._db, obj_in=installation)
            self._db.commit()
            logger.info(f"Persisted installation record for workflow '{workflow_id}' with job_id {job_id}")
        except Exception as e:
            logger.error(f"Failed to persist installation record for workflow '{workflow_id}': {e}")
            self._db.rollback()
            # Don't fail the installation if DB persist fails, but log it

        return job_id

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

        # Remove from database
        try:
            db_obj = workflow_installation_repo.get_by_job_id(self._db, job_id=job_id)
            if db_obj:
                workflow_installation_repo.remove(self._db, id=db_obj.id)
                self._db.commit()
                logger.info(f"Removed installation record for job_id {job_id}")
        except Exception as e:
            logger.error(f"Failed to remove installation record for job_id {job_id}: {e}")
            self._db.rollback()

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

        # Handle cluster configuration
        # If job_cluster_id is None, tasks will use Databricks serverless compute
        # by omitting cluster parameters (existing_cluster_id, new_cluster)
        if isinstance(wf.get("tasks"), list):
            for t in wf["tasks"]:
                if job_cluster_id:
                    # Set the configured cluster ID, overriding any placeholder
                    if "new_cluster" not in t:
                        t["existing_cluster_id"] = job_cluster_id
                else:
                    # Remove placeholder cluster IDs to enable serverless
                    if t.get("existing_cluster_id") in ["cluster-id", ""]:
                        del t["existing_cluster_id"]

        # Resolve relative paths to absolute workspace paths
        # Use WORKSPACE_APP_PATH from settings if available, otherwise derive from __file__
        if self._settings and self._settings.WORKSPACE_APP_PATH:
            # Use configured workspace path (for local dev with remote jobs)
            base_path = self._settings.WORKSPACE_APP_PATH
        else:
            # Derive from __file__ (works when app runs in workspace)
            base_path = str(Path(__file__).parent.parent)

        if isinstance(wf.get("tasks"), list):
            for t in wf["tasks"]:
                # Handle notebook_task
                if 'notebook_task' in t and isinstance(t['notebook_task'], dict):
                    notebook_path = t['notebook_task'].get('notebook_path', '')
                    if notebook_path and not notebook_path.startswith('/'):
                        # Convert to workspace path: workflows are relative to src directory
                        workspace_path = f"{base_path}/workflows/{workflow_id}/{notebook_path}"
                        t['notebook_task']['notebook_path'] = workspace_path

                # Handle spark_python_task
                if 'spark_python_task' in t and isinstance(t['spark_python_task'], dict):
                    python_file = t['spark_python_task'].get('python_file', '')
                    if python_file and not python_file.startswith('/'):
                        # Convert to workspace path: workflows are relative to src directory
                        workspace_path = f"{base_path}/workflows/{workflow_id}/{python_file}"
                        t['spark_python_task']['python_file'] = workspace_path

        return wf

    def _build_tasks_from_definition(self, wf: Dict[str, Any]) -> List[jobs.Task]:
        tasks: List[jobs.Task] = []
        for t in wf.get('tasks', []) or []:
            if not isinstance(t, dict):
                continue
            kwargs: Dict[str, Any] = {}
            if 'task_key' in t:
                kwargs['task_key'] = t['task_key']
            # Only set cluster params if they exist in task definition
            # Omitting them enables Databricks serverless compute
            if 'existing_cluster_id' in t:
                kwargs['existing_cluster_id'] = t['existing_cluster_id']
            if 'notebook_task' in t and isinstance(t['notebook_task'], dict):
                kwargs['notebook_task'] = jobs.NotebookTask(**t['notebook_task'])
            if 'spark_python_task' in t and isinstance(t['spark_python_task'], dict):
                kwargs['spark_python_task'] = jobs.SparkPythonTask(**t['spark_python_task'])
            if 'python_wheel_task' in t and isinstance(t['python_wheel_task'], dict):
                kwargs['python_wheel_task'] = jobs.PythonWheelTask(**t['python_wheel_task'])

            task_obj = jobs.Task(**kwargs)
            tasks.append(task_obj)

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

    def cancel_run(self, run_id: int) -> None:
        """Cancel a running job.

        Args:
            run_id: ID of the job run to cancel

        Raises:
            Exception: If cancellation fails
        """
        try:
            self._client.jobs.cancel_run(run_id=run_id)
            logger.info(f"Cancelled run {run_id}")
        except Exception as e:
            logger.error(f"Error cancelling run {run_id}: {e}")
            raise

    def start_background_polling(self, interval_seconds: int = 300):
        """Start background polling of installed job states.

        Args:
            interval_seconds: Polling interval (default: 5 minutes)
        """
        if self._polling_thread and self._polling_thread.is_alive():
            logger.warning("Background polling already running")
            return

        self._stop_polling.clear()
        self._polling_thread = threading.Thread(
            target=self._poll_job_states,
            args=(interval_seconds,),
            daemon=True,
            name="JobsManagerPoller"
        )
        self._polling_thread.start()
        logger.info(f"Started background job polling (interval: {interval_seconds}s)")

    def stop_background_polling(self):
        """Stop background polling."""
        if not self._polling_thread or not self._polling_thread.is_alive():
            logger.warning("Background polling not running")
            return

        self._stop_polling.set()
        self._polling_thread.join(timeout=10)
        logger.info("Stopped background job polling")

    def _poll_job_states(self, interval_seconds: int):
        """Background task to poll all installed jobs."""
        from src.common.database import get_db

        logger.info("Job state polling thread started")

        while not self._stop_polling.is_set():
            # Create a new database session for this polling iteration
            db = next(get_db())
            try:
                # Get all installed workflows from database
                installations = workflow_installation_repo.get_all_installed(db)
                logger.info(f"Polling {len(installations)} installed workflows...")

                for installation in installations:
                    if self._stop_polling.is_set():
                        break

                    try:
                        # Get recent runs for this job (limit to reasonable number to avoid overwhelming)
                        runs = self._client.jobs.list_runs(job_id=installation.job_id, limit=10)
                        if not runs:
                            continue

                        # Process each run
                        for run in runs:
                            if not run or not run.state:
                                continue

                            # Build run data dict
                            run_data = {
                                'run_name': run.run_name,
                                'life_cycle_state': run.state.life_cycle_state.value if run.state.life_cycle_state else None,
                                'result_state': run.state.result_state.value if run.state.result_state else None,
                                'state_message': run.state.state_message if run.state else None,
                                'start_time': run.start_time,
                                'end_time': run.end_time
                            }

                            # Upsert job run record (creates or updates)
                            job_run = workflow_job_run_repo.upsert_run(
                                db,
                                run_id=run.run_id,
                                workflow_installation_id=installation.id,
                                run_data=run_data
                            )

                            # Create notification if job terminated unsuccessfully (failed, canceled, timed out, etc.)
                            if (run.state.life_cycle_state == RunLifeCycleState.TERMINATED and
                                run.state.result_state != RunResultState.SUCCESS):

                                # Check if we've already notified about this failure
                                if not job_run.notified_at:
                                    logger.info(f"Job {installation.workflow_id} (run {run.run_id}) failed, creating notification")
                                    try:
                                        self._create_job_failure_notification(
                                            installation.name,
                                            installation.workflow_id,
                                            run.run_id
                                        )
                                        # Mark this run as notified only after notification succeeds
                                        workflow_job_run_repo.mark_as_notified(db, run_id=run.run_id)
                                    except Exception as e:
                                        logger.error(f"Failed to create notification for run {run.run_id}: {e}")
                                        # Don't mark as notified so we can retry on next poll
                                else:
                                    logger.debug(f"Already notified about failure of run {run.run_id}, skipping")

                        # Update last polled timestamp on installation (use latest run if available)
                        latest_run = next(iter(runs), None)
                        if latest_run and latest_run.state:
                            latest_run_data = {
                                'run_id': latest_run.run_id,
                                'life_cycle_state': latest_run.state.life_cycle_state.value if latest_run.state.life_cycle_state else None,
                                'result_state': latest_run.state.result_state.value if latest_run.state.result_state else None,
                                'start_time': latest_run.start_time,
                                'end_time': latest_run.end_time
                            }
                            workflow_installation_repo.update_last_polled(
                                db,
                                workflow_id=installation.workflow_id,
                                job_state=latest_run_data
                            )

                    except Exception as e:
                        logger.error(f"Error polling job {installation.job_id} ({installation.workflow_id}): {e}")

                # Commit all updates
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Error committing polling updates: {e}")
                    db.rollback()

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            finally:
                # Always close the session
                db.close()

            # Wait for next interval or stop signal (unless stopping)
            if not self._stop_polling.is_set():
                self._stop_polling.wait(timeout=interval_seconds)

        logger.info("Job state polling thread stopped")

    def _create_job_failure_notification(self, job_name: str, workflow_id: str, run_id: int):
        """Create a notification for job failure."""
        if not self._notifications_manager:
            return

        try:
            from src.models.notifications import Notification, NotificationType

            notification = Notification(
                id=f"job-failure-{workflow_id}-{run_id}-{int(time.time())}",
                type=NotificationType.ERROR,
                title=f"Background Job Failed: {job_name}",
                message=f"Workflow '{job_name}' (ID: {workflow_id}) failed during scheduled execution. Run ID: {run_id}",
                data={
                    "workflow_id": workflow_id,
                    "job_name": job_name,
                    "run_id": run_id,
                    "error_type": "job_failure"
                },
                target_roles=["Admin"],  # Notify admins
                created_at=datetime.utcnow()
            )

            self._notifications_manager.create_notification(notification, db=self._db)
            logger.info(f"Created failure notification for workflow '{workflow_id}' run {run_id}")

        except Exception as e:
            logger.error(f"Failed to create failure notification for workflow '{workflow_id}': {e}")


