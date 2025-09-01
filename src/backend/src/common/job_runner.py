from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import JobSettings
from databricks.sdk.service.workspace import ImportFormat
from fastapi import Depends

from .config import Settings, get_settings
from .logging import get_logger
from .workspace_client import get_workspace_client

logger = get_logger(__name__)

class JobRunner:
    """Manages Databricks workflow jobs."""

    def __init__(self, client: WorkspaceClient, settings: Settings) -> None:
        """Initialize the job runner with Databricks workspace client.
        
        Args:
            client: Databricks workspace client instance
            settings: Application settings
        """
        self.client = client
        self.workflows_dir = Path(__file__).parent.parent / "workflows"
        self.settings = settings

    def _ensure_volume_exists(self) -> str:
        """Ensure the configured volume exists and return its path.
        
        Returns:
            Full path to the volume
            
        Raises:
            Exception: If volume creation fails
        """
        try:
            # Get volume info
            volume_path = f"{self.settings.DATABRICKS_CATALOG}.{self.settings.DATABRICKS_SCHEMA}.{self.settings.DATABRICKS_VOLUME}"

            try:
                volume = self.client.volumes.get(volume_path)
                logger.info(f"Using existing volume: {volume_path}")
            except Exception:
                # Volume doesn't exist, create it
                logger.info(f"Creating volume: {volume_path}")
                volume = self.client.volumes.create(
                    catalog_name=self.settings.DATABRICKS_CATALOG,
                    schema_name=self.settings.DATABRICKS_SCHEMA,
                    name=self.settings.DATABRICKS_VOLUME,
                    volume_type="MANAGED"
                )

            return volume_path

        except Exception as e:
            logger.error(f"Error ensuring volume exists: {e!s}")
            raise

    def deploy_job_code(self, job_name: str) -> Optional[str]:
        """Deploy job code to Databricks workspace.
        
        Args:
            job_name: Name of the job (corresponds to directory in workflows/)
            
        Returns:
            Base path in workspace where code was deployed, or None if failed
            
        Raises:
            FileNotFoundError: If job code directory doesn't exist
        """
        job_dir = self.workflows_dir / job_name
        if not job_dir.exists():
            raise FileNotFoundError(f"Job directory not found: {job_name}")

        try:
            # Ensure volume exists
            volume_path = self._ensure_volume_exists()

            # Create a directory in the volume for this job
            job_volume_path = f"{volume_path}/jobs/{job_name}"

            # Deploy all files from the job directory
            for file_path in job_dir.rglob("*"):
                if file_path.is_file():
                    # Skip the workflow.yaml file as it's not needed in the volume
                    if file_path.name == "workflow.yaml":
                        continue

                    # Calculate relative path for volume
                    rel_path = file_path.relative_to(job_dir)
                    volume_file_path = f"{job_volume_path}/{rel_path}"

                    # Create parent directories if needed
                    if rel_path.parent != Path("."):
                        self.client.workspace.mkdirs(f"{job_volume_path}/{rel_path.parent}")

                    # Determine file type and import format
                    if file_path.suffix == ".py":
                        format = ImportFormat.SOURCE
                    elif file_path.suffix == ".ipynb":
                        format = ImportFormat.JUPYTER
                    else:
                        format = ImportFormat.AUTO

                    # Import the file
                    with open(file_path, "rb") as f:
                        self.client.workspace.import_(
                            path=volume_file_path,
                            format=format,
                            content=f.read()
                        )

            logger.info(f"Deployed job code for {job_name} to {job_volume_path}")
            return job_volume_path

        except Exception as e:
            logger.error(f"Error deploying job code for {job_name}: {e!s}")
            return None

    def create_job_from_yaml(self, job_name: str) -> Optional[int]:
        """Create a job from a workflow YAML file.
        
        Args:
            job_name: Name of the job (corresponds to directory in workflows/)
            
        Returns:
            Job ID if successful, None otherwise
            
        Raises:
            FileNotFoundError: If workflow file doesn't exist
            yaml.YAMLError: If workflow file contains invalid YAML
        """
        workflow_file = self.workflows_dir / job_name / "workflow.yaml"
        if not workflow_file.exists():
            raise FileNotFoundError(f"Workflow file not found: {job_name}/workflow.yaml")

        try:
            with open(workflow_file) as f:
                workflow_config = yaml.safe_load(f)

            # Deploy job code first
            volume_path = self.deploy_job_code(job_name)
            if not volume_path:
                raise Exception(f"Failed to deploy job code for {job_name}")

            # Update notebook paths in tasks to use volume paths
            for task in workflow_config['tasks']:
                if 'notebook_task' in task:
                    notebook_path = task['notebook_task']['notebook_path']
                    # Convert relative path to volume path
                    if not notebook_path.startswith('/'):
                        notebook_path = f"{volume_path}/{notebook_path}"
                    task['notebook_task']['notebook_path'] = notebook_path

            # Create job settings from workflow config
            job_settings = JobSettings(
                name=workflow_config['name'],
                format=workflow_config['format'],
                tasks=workflow_config['tasks']
            )

            # Create the job
            job = self.client.jobs.create(**job_settings.as_dict())
            logger.info(f"Created job {job.job_id} from workflow {job_name}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error creating job from workflow {job_name}: {e!s}")
            return None

    def create_job(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        schedule: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> int:
        """Create a new Databricks job.
        
        Args:
            name: Name of the job
            tasks: List of task configurations
            schedule: Optional schedule configuration
            tags: Optional tags for the job
            
        Returns:
            Job ID
            
        Raises:
            Exception: If job creation fails
        """
        try:
            job_config = {
                "name": name,
                "tasks": tasks,
                "tags": tags or {}
            }

            if schedule:
                job_config["schedule"] = schedule

            job = self.client.jobs.create(**job_config)
            logger.info(f"Created job {name} with ID {job.job_id}")
            return job.job_id

        except Exception as e:
            logger.error(f"Error creating job {name}: {e!s}")
            raise

    def run_job(self, job_id: int) -> int:
        """Run a Databricks job.
        
        Args:
            job_id: ID of the job to run
            
        Returns:
            Run ID
            
        Raises:
            Exception: If job run fails
        """
        try:
            run = self.client.jobs.run_now(job_id=job_id)
            logger.info(f"Started job run {run.run_id} for job {job_id}")
            return run.run_id

        except Exception as e:
            logger.error(f"Error running job {job_id}: {e!s}")
            raise

    def get_run_status(self, run_id: int) -> Dict[str, Any]:
        """Get the status of a job run.
        
        Args:
            run_id: ID of the job run
            
        Returns:
            Dictionary containing run status information
            
        Raises:
            Exception: If status retrieval fails
        """
        try:
            run = self.client.jobs.get_run(run_id=run_id)
            return {
                "run_id": run.run_id,
                "job_id": run.job_id,
                "life_cycle_state": run.state.life_cycle_state,
                "result_state": run.state.result_state,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "tasks": [
                    {
                        "task_key": task.task_key,
                        "life_cycle_state": task.state.life_cycle_state,
                        "result_state": task.state.result_state,
                        "start_time": task.start_time,
                        "end_time": task.end_time
                    }
                    for task in run.tasks
                ]
            }

        except Exception as e:
            logger.error(f"Error getting status for run {run_id}: {e!s}")
            raise

    def cancel_run(self, run_id: int) -> None:
        """Cancel a running job.
        
        Args:
            run_id: ID of the job run to cancel
            
        Raises:
            Exception: If cancellation fails
        """
        try:
            self.client.jobs.cancel_run(run_id=run_id)
            logger.info(f"Cancelled run {run_id}")

        except Exception as e:
            logger.error(f"Error cancelling run {run_id}: {e!s}")
            raise

    def delete_job(self, job_id: int) -> None:
        """Delete a Databricks job.
        
        Args:
            job_id: ID of the job to delete
            
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.jobs.delete(job_id=job_id)
            logger.info(f"Deleted job {job_id}")

        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e!s}")
            raise

def get_job_runner(
    client: WorkspaceClient = Depends(get_workspace_client),
    settings: Settings = Depends(get_settings)
) -> JobRunner:
    """Get a configured job runner instance.
    
    Args:
        client: Cached workspace client (injected by FastAPI)
        settings: Application settings (injected by FastAPI)
        
    Returns:
        Configured job runner instance
    """
    return JobRunner(client, settings)
