import logging
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.repositories.projects_repository import project_repo
from src.repositories.teams_repository import team_repo
from src.models.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRead,
    ProjectSummary,
    UserProjectAccess,
    ProjectTeamAssignment
)
from src.db_models.projects import ProjectDb
from src.common.logging import get_logger
from src.common.errors import ConflictError, NotFoundError

logger = get_logger(__name__)


class ProjectsManager:
    def __init__(self):
        self.project_repo = project_repo
        self.team_repo = team_repo
        logger.debug("ProjectsManager initialized.")

    def _serialize_list_fields(self, data: dict) -> dict:
        """Helper to serialize list fields to JSON strings for database storage."""
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = json.dumps(data['tags'])
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = json.dumps(data['metadata'])
        return data

    def _convert_db_to_read_model(self, db_project: ProjectDb) -> ProjectRead:
        """Helper to convert DB model to Read model."""
        return ProjectRead.model_validate(db_project)

    def _convert_db_to_summary_model(self, db_project: ProjectDb) -> ProjectSummary:
        """Helper to convert DB model to Summary model."""
        return ProjectSummary(
            id=db_project.id,
            name=db_project.name,
            title=db_project.title,
            team_count=len(db_project.teams) if db_project.teams else 0
        )

    # Project CRUD operations
    def create_project(self, db: Session, project_in: ProjectCreate, current_user_id: str) -> ProjectRead:
        """Creates a new project."""
        logger.debug(f"Attempting to create project: {project_in.name}")

        # Check if project name already exists
        existing_project = self.project_repo.get_by_name(db, name=project_in.name)
        if existing_project:
            raise ConflictError(f"Project with name '{project_in.name}' already exists.")

        # Prepare data for database
        db_obj_data = project_in.model_dump(exclude_unset=True, exclude={'team_ids'})
        db_obj_data['created_by'] = current_user_id
        db_obj_data['updated_by'] = current_user_id
        self._serialize_list_fields(db_obj_data)

        db_project = ProjectDb(**db_obj_data)

        try:
            db.add(db_project)
            db.flush()
            db.refresh(db_project)

            # Assign initial teams if provided
            if project_in.team_ids:
                for team_id in project_in.team_ids:
                    self.assign_team_to_project(db, project_id=db_project.id, team_id=team_id, assigned_by=current_user_id)

            logger.info(f"Successfully created project '{db_project.name}' with id: {db_project.id}")

            # Reload with teams
            db_project = self.project_repo.get_with_teams(db, db_project.id)
            return self._convert_db_to_read_model(db_project)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating project '{project_in.name}': {e}")
            if "unique constraint" in str(e).lower():
                raise ConflictError(f"Project with name '{project_in.name}' already exists.")
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error creating project '{project_in.name}': {e}")
            raise

    def get_project_by_id(self, db: Session, project_id: str) -> Optional[ProjectRead]:
        """Gets a project by its ID, including teams."""
        logger.debug(f"Fetching project with id: {project_id}")
        db_project = self.project_repo.get_with_teams(db, project_id)
        if not db_project:
            return None
        return self._convert_db_to_read_model(db_project)

    def get_all_projects(self, db: Session, skip: int = 0, limit: int = 100) -> List[ProjectRead]:
        """Gets a list of all projects."""
        logger.debug(f"Fetching projects with skip={skip}, limit={limit}")
        db_projects = self.project_repo.get_multi_with_teams(db, skip=skip, limit=limit)
        return [self._convert_db_to_read_model(project) for project in db_projects]

    def get_projects_summary(self, db: Session) -> List[ProjectSummary]:
        """Gets a summary list of projects for dropdowns/selection."""
        logger.debug("Fetching projects summary")
        db_projects = self.project_repo.get_multi_with_teams(db, limit=1000)
        return [self._convert_db_to_summary_model(project) for project in db_projects]

    def get_user_projects(self, db: Session, user_identifier: str, user_groups: List[str]) -> UserProjectAccess:
        """Gets all projects that a user has access to through team membership."""
        logger.debug(f"Fetching accessible projects for user: {user_identifier}")

        try:
            db_projects = self.project_repo.get_projects_for_user(db, user_identifier, user_groups)
            project_summaries = [self._convert_db_to_summary_model(project) for project in db_projects]

            return UserProjectAccess(
                projects=project_summaries,
                current_project_id=None  # This would be set by session/context management
            )
        except Exception as e:
            logger.exception(f"Error fetching user projects: {e}")
            return UserProjectAccess(projects=[], current_project_id=None)

    def update_project(self, db: Session, project_id: str, project_in: ProjectUpdate, current_user_id: str) -> Optional[ProjectRead]:
        """Updates an existing project."""
        logger.debug(f"Attempting to update project with id: {project_id}")

        db_project = self.project_repo.get(db, project_id)
        if not db_project:
            raise NotFoundError(f"Project with id '{project_id}' not found.")

        # Check for name conflicts if name is being updated
        if project_in.name and project_in.name != db_project.name:
            existing_project = self.project_repo.get_by_name(db, name=project_in.name)
            if existing_project:
                raise ConflictError(f"Project with name '{project_in.name}' already exists.")

        update_data = project_in.model_dump(exclude_unset=True)
        update_data['updated_by'] = current_user_id
        self._serialize_list_fields(update_data)

        try:
            updated_db_project = self.project_repo.update(db=db, db_obj=db_project, obj_in=update_data)
            db.flush()
            db.refresh(updated_db_project)
            logger.info(f"Successfully updated project '{updated_db_project.name}' (id: {project_id})")

            # Reload with teams
            updated_db_project = self.project_repo.get_with_teams(db, project_id)
            return self._convert_db_to_read_model(updated_db_project)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error updating project {project_id}: {e}")
            if "unique constraint" in str(e).lower():
                raise ConflictError(f"Project name '{project_in.name}' is already in use.")
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error updating project {project_id}: {e}")
            raise

    def delete_project(self, db: Session, project_id: str) -> Optional[ProjectRead]:
        """Deletes a project by its ID."""
        logger.debug(f"Attempting to delete project with id: {project_id}")

        db_project = self.project_repo.get_with_teams(db, project_id)
        if not db_project:
            raise NotFoundError(f"Project with id '{project_id}' not found.")

        read_model = self._convert_db_to_read_model(db_project)

        try:
            self.project_repo.remove(db=db, id=project_id)
            logger.info(f"Successfully deleted project '{read_model.name}' (id: {project_id})")
            return read_model
        except Exception as e:
            db.rollback()
            logger.exception(f"Error deleting project {project_id}: {e}")
            raise

    # Team assignment operations
    def assign_team_to_project(self, db: Session, project_id: str, team_id: str, assigned_by: str) -> bool:
        """Assigns a team to a project."""
        logger.debug(f"Assigning team {team_id} to project {project_id}")

        # Verify project exists
        db_project = self.project_repo.get(db, project_id)
        if not db_project:
            raise NotFoundError(f"Project with id '{project_id}' not found.")

        # Verify team exists
        db_team = self.team_repo.get(db, team_id)
        if not db_team:
            raise NotFoundError(f"Team with id '{team_id}' not found.")

        try:
            success = self.project_repo.assign_team(db, project_id=project_id, team_id=team_id, assigned_by=assigned_by)
            if not success:
                raise ConflictError(f"Team '{db_team.name}' is already assigned to project '{db_project.name}'.")

            logger.info(f"Successfully assigned team '{db_team.name}' to project '{db_project.name}'")
            return True
        except ConflictError:
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error assigning team to project: {e}")
            raise

    def remove_team_from_project(self, db: Session, project_id: str, team_id: str) -> bool:
        """Removes a team from a project."""
        logger.debug(f"Removing team {team_id} from project {project_id}")

        try:
            success = self.project_repo.remove_team(db, project_id=project_id, team_id=team_id)
            if success:
                logger.info(f"Successfully removed team from project")
            else:
                logger.warning(f"Team {team_id} was not assigned to project {project_id}")
            return success
        except Exception as e:
            db.rollback()
            logger.exception(f"Error removing team from project: {e}")
            raise

    def get_project_teams(self, db: Session, project_id: str) -> List[dict]:
        """Gets all teams assigned to a project."""
        logger.debug(f"Fetching teams for project: {project_id}")

        # Verify project exists
        db_project = self.project_repo.get(db, project_id)
        if not db_project:
            raise NotFoundError(f"Project with id '{project_id}' not found.")

        db_teams = self.project_repo.get_team_assignments(db, project_id)
        return [{"id": team.id, "name": team.name, "title": team.title} for team in db_teams]

    def check_user_project_access(self, db: Session, user_identifier: str, user_groups: List[str], project_id: str) -> bool:
        """Checks if a user has access to a specific project."""
        logger.debug(f"Checking project access for user {user_identifier} to project {project_id}")

        user_projects = self.project_repo.get_projects_for_user(db, user_identifier, user_groups)
        return any(project.id == project_id for project in user_projects)


# Singleton instance
projects_manager = ProjectsManager()