from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import git
import yaml

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

class GitService:
    """Service for managing YAML files in a Git repository."""

    def __init__(self) -> None:
        """Initialize the Git service."""
        settings = get_settings()
        self.repo_url = settings.GIT_REPO_URL
        self.branch = settings.GIT_BRANCH
        self.username = settings.GIT_USERNAME
        self.password = settings.GIT_PASSWORD

        if not all([self.repo_url, self.username, self.password]):
            logger.warning("Git repository not configured")
            return

        self.repo_dir = Path('api/data/git')
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._init_repo()
        except Exception as e:
            logger.error(f"Error initializing Git repository: {e!s}")

    def _init_repo(self) -> None:
        """Initialize or update the Git repository."""
        if not (self.repo_dir / '.git').exists():
            logger.info(f"Cloning repository {self.repo_url}")
            self.repo = git.Repo.clone_from(
                self.repo_url,
                self.repo_dir,
                branch=self.branch,
                env={
                    'GIT_USERNAME': self.username,
                    'GIT_PASSWORD': self.password
                }
            )
        else:
            logger.info("Updating existing repository")
            self.repo = git.Repo(self.repo_dir)
            self.repo.git.pull(
                'origin',
                self.branch,
                env={
                    'GIT_USERNAME': self.username,
                    'GIT_PASSWORD': self.password
                }
            )

    def save_yaml(
        self,
        filename: str,
        data: Dict[str, Any],
        commit_message: Optional[str] = None
    ) -> bool:
        """Save data to a YAML file and commit to Git.
        
        Args:
            filename: Name of the YAML file
            data: Dictionary to save as YAML
            commit_message: Optional commit message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.repo_url:
            logger.warning("Git repository not configured")
            return False

        try:
            # Save YAML file
            file_path = self.repo_dir / filename
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)

            # Stage and commit changes
            self.repo.index.add([str(file_path)])

            if not commit_message:
                commit_message = f"Update {filename} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

            self.repo.index.commit(commit_message)

            # Push changes
            self.repo.git.push(
                'origin',
                self.branch,
                env={
                    'GIT_USERNAME': self.username,
                    'GIT_PASSWORD': self.password
                }
            )

            logger.info(f"Successfully saved and committed {filename}")
            return True

        except Exception as e:
            logger.error(f"Error saving YAML file to Git: {e!s}")
            return False

    def load_yaml(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a YAML file from the Git repository.
        
        Args:
            filename: Name of the YAML file
            
        Returns:
            Dictionary containing the YAML data, or None if not found
        """
        if not self.repo_url:
            logger.warning("Git repository not configured")
            return None

        try:
            file_path = self.repo_dir / filename
            if not file_path.exists():
                return None

            with open(file_path) as f:
                return yaml.safe_load(f)

        except Exception as e:
            logger.error(f"Error loading YAML file from Git: {e!s}")
            return None

    def list_files(self, pattern: str = "*.yaml") -> List[str]:
        """List YAML files in the repository.
        
        Args:
            pattern: Glob pattern to match files
            
        Returns:
            List of matching file names
        """
        if not self.repo_url:
            logger.warning("Git repository not configured")
            return []

        try:
            return [
                str(f.relative_to(self.repo_dir))
                for f in self.repo_dir.glob(pattern)
            ]

        except Exception as e:
            logger.error(f"Error listing files in Git repository: {e!s}")
            return []

# Global Git service instance
git_service: Optional[GitService] = None

def init_git_service() -> None:
    """Initialize the global Git service instance."""
    global git_service
    git_service = GitService()

def get_git_service() -> GitService:
    """Get the global Git service instance.
    
    Returns:
        Git service
        
    Raises:
        RuntimeError: If Git service is not initialized
    """
    if not git_service:
        raise RuntimeError("Git service not initialized")
    return git_service
