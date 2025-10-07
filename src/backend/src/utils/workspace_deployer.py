"""Workspace Deployer - Deploy workflow code to Databricks workspace.

This utility handles deploying local workflow code to the Databricks workspace
for use by job tasks. This is necessary for containerized Databricks Apps where
job clusters cannot access the container filesystem.
"""
from pathlib import Path
from typing import Optional, Set
import base64

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

from src.common.logging import get_logger

logger = get_logger(__name__)


class WorkspaceDeployer:
    """Deploy workflow code to Databricks workspace."""

    def __init__(self, ws_client: WorkspaceClient, deployment_path: Optional[str] = None):
        """Initialize the deployer.

        Args:
            ws_client: Databricks workspace client
            deployment_path: Base workspace path for deployments (e.g., /Workspace/Users/.../workflows)
        """
        self._client = ws_client
        self._deployment_path = deployment_path
        self._deployed_workflows: Set[str] = set()  # Track deployed workflow IDs

    def deploy_workflow(self, workflow_id: str, workflow_dir: Path) -> str:
        """Deploy a workflow folder to the workspace.

        Copies all files from the local workflow directory to the workspace deployment path.
        Uses Databricks Workspace API to upload files.

        Args:
            workflow_id: Unique workflow identifier
            workflow_dir: Local path to workflow directory

        Returns:
            Workspace path where workflow was deployed

        Raises:
            ValueError: If deployment path is not configured
            RuntimeError: If deployment fails
        """
        if not self._deployment_path:
            raise ValueError(
                "WORKSPACE_DEPLOYMENT_PATH not configured. "
                "Set this environment variable to deploy workflows for containerized Apps."
            )

        if not workflow_dir.exists() or not workflow_dir.is_dir():
            raise ValueError(f"Workflow directory does not exist: {workflow_dir}")

        # Target workspace path for this workflow
        target_path = f"{self._deployment_path}/{workflow_id}"

        # Skip if already deployed in this session
        if workflow_id in self._deployed_workflows:
            logger.debug(f"Workflow '{workflow_id}' already deployed to {target_path}")
            return target_path

        logger.info(f"Deploying workflow '{workflow_id}' from {workflow_dir} to {target_path}")

        try:
            # Create parent directory and workflow directory if needed
            self._ensure_directory_exists(self._deployment_path)
            self._ensure_directory_exists(target_path)

            # Upload all files in the workflow directory
            for file_path in workflow_dir.iterdir():
                if file_path.is_file():
                    self._upload_file(file_path, f"{target_path}/{file_path.name}")
                elif file_path.is_dir():
                    # Recursively upload subdirectories
                    self._upload_directory(file_path, f"{target_path}/{file_path.name}")

            # Track successful deployment
            self._deployed_workflows.add(workflow_id)
            logger.info(f"Successfully deployed workflow '{workflow_id}' to {target_path}")

            return target_path

        except Exception as e:
            logger.error(f"Failed to deploy workflow '{workflow_id}': {e}")
            raise RuntimeError(f"Workflow deployment failed: {e}") from e

    def _ensure_directory_exists(self, workspace_path: str) -> None:
        """Create a workspace directory if it doesn't exist.

        Args:
            workspace_path: Workspace path to create
        """
        try:
            # Try to get the object to see if it exists
            try:
                self._client.workspace.get_status(workspace_path)
                logger.debug(f"Directory already exists: {workspace_path}")
                return
            except Exception:
                # Directory doesn't exist, create it
                pass

            # Create the directory
            self._client.workspace.mkdirs(workspace_path)
            logger.debug(f"Created workspace directory: {workspace_path}")

        except Exception as e:
            logger.error(f"Failed to create directory {workspace_path}: {e}")
            raise

    def _upload_file(self, local_path: Path, workspace_path: str) -> None:
        """Upload a single file to the workspace.

        Args:
            local_path: Local file path
            workspace_path: Target workspace path
        """
        try:
            # Read file content
            with open(local_path, 'rb') as f:
                content = f.read()

            # Encode content as base64
            encoded_content = base64.b64encode(content).decode('utf-8')

            # Determine format based on file extension
            if local_path.suffix in ['.py', '.yaml', '.yml', '.txt', '.json', '.md']:
                format_type = workspace.ImportFormat.AUTO
            else:
                format_type = workspace.ImportFormat.AUTO

            # Upload using workspace import API
            self._client.workspace.import_(
                path=workspace_path,
                content=encoded_content,
                format=format_type,
                overwrite=True
            )

            logger.debug(f"Uploaded file: {local_path.name} -> {workspace_path}")

        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            raise

    def _upload_directory(self, local_dir: Path, workspace_path: str) -> None:
        """Recursively upload a directory to the workspace.

        Args:
            local_dir: Local directory path
            workspace_path: Target workspace path
        """
        # Create the directory
        self._ensure_directory_exists(workspace_path)

        # Upload all files and subdirectories
        for item in local_dir.iterdir():
            if item.is_file():
                self._upload_file(item, f"{workspace_path}/{item.name}")
            elif item.is_dir():
                self._upload_directory(item, f"{workspace_path}/{item.name}")

    def is_deployed(self, workflow_id: str) -> bool:
        """Check if a workflow has been deployed in this session.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if deployed, False otherwise
        """
        return workflow_id in self._deployed_workflows

    def clear_deployment_cache(self) -> None:
        """Clear the deployment tracking cache.

        This forces all workflows to be redeployed on next install.
        Useful for development or when workflow code has changed.
        """
        self._deployed_workflows.clear()
        logger.info("Cleared deployment cache")
