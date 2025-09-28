import logging
import json
import yaml
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.repositories.projects_repository import project_repo
from src.repositories.teams_repository import team_repo
from src.controller.tags_manager import TagsManager
from src.models.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRead,
    ProjectSummary,
    UserProjectAccess,
    ProjectTeamAssignment,
    ProjectAccessRequest,
    ProjectAccessRequestResponse
)
from src.models.tags import AssignedTag, AssignedTagCreate
from src.db_models.projects import ProjectDb
from src.common.logging import get_logger
from src.common.errors import ConflictError, NotFoundError
from src.models.notifications import NotificationType

logger = get_logger(__name__)


class ProjectsManager:
    def __init__(self, tags_manager: Optional[TagsManager] = None):
        self.project_repo = project_repo
        self.team_repo = team_repo
        self.tags_manager = tags_manager or TagsManager()
        logger.debug("ProjectsManager initialized.")

    def _serialize_list_fields(self, data: dict) -> dict:
        """Helper to serialize list fields to JSON strings for database storage."""
        # Tags are now handled through TagsManager, remove from data
        if 'tags' in data:
            del data['tags']
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = json.dumps(data['metadata'])
        return data

    def _convert_db_to_read_model(self, db_project: ProjectDb, db: Optional[Session] = None) -> ProjectRead:
        """Helper to convert DB model to Read model."""
        project_read = ProjectRead.model_validate(db_project)

        # Set owner_team_name from the owner_team relationship
        if db_project.owner_team:
            project_read.owner_team_name = db_project.owner_team.name

        # Load tags from TagsManager
        if db:
            try:
                assigned_tags = self.tags_manager.list_assigned_tags(
                    db, entity_id=db_project.id, entity_type="project"
                )
                project_read.tags = assigned_tags
            except Exception as e:
                logger.warning(f"Failed to load tags for project {db_project.id}: {e}")
                project_read.tags = []

        return project_read

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

        # Extract tags before serialization
        tags_data = db_obj_data.get('tags', [])
        self._serialize_list_fields(db_obj_data)

        db_project = ProjectDb(**db_obj_data)

        try:
            db.add(db_project)
            db.flush()
            db.refresh(db_project)

            # Handle tags if provided
            if tags_data:
                # Convert string tags to AssignedTagCreate objects
                tag_creates = []
                for tag in tags_data:
                    if isinstance(tag, str):
                        tag_creates.append(AssignedTagCreate(tag_fqn=tag))
                    elif isinstance(tag, dict):
                        tag_creates.append(AssignedTagCreate(**tag))

                if tag_creates:
                    self.tags_manager.set_tags_for_entity(
                        db, entity_id=db_project.id, entity_type="project",
                        tags=tag_creates, user_email=current_user_id
                    )

            # Assign initial teams if provided
            if project_in.team_ids:
                for team_id in project_in.team_ids:
                    self.assign_team_to_project(db, project_id=db_project.id, team_id=team_id, assigned_by=current_user_id)

            logger.info(f"Successfully created project '{db_project.name}' with id: {db_project.id}")

            # Reload with teams
            db_project = self.project_repo.get_with_teams(db, db_project.id)
            return self._convert_db_to_read_model(db_project, db)
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
            # Check if user is admin
            is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
            logger.debug(f"User {user_identifier} admin status: {is_admin}")

            if is_admin:
                # Admins see all projects
                logger.debug(f"User {user_identifier} is admin, showing all projects")
                db_projects = self.project_repo.get_multi(db)
            else:
                # Non-admins only see projects they have team access to
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

        # Extract tags before serialization
        tags_data = update_data.get('tags')
        self._serialize_list_fields(update_data)

        try:
            updated_db_project = self.project_repo.update(db=db, db_obj=db_project, obj_in=update_data)
            db.flush()
            db.refresh(updated_db_project)

            # Handle tags if provided
            if tags_data is not None:  # Allow empty list to clear tags
                # Convert string tags to AssignedTagCreate objects
                tag_creates = []
                for tag in tags_data:
                    if isinstance(tag, str):
                        tag_creates.append(AssignedTagCreate(tag_fqn=tag))
                    elif isinstance(tag, dict):
                        tag_creates.append(AssignedTagCreate(**tag))

                self.tags_manager.set_tags_for_entity(
                    db, entity_id=updated_db_project.id, entity_type="project",
                    tags=tag_creates, user_email=current_user_id
                )

            logger.info(f"Successfully updated project '{updated_db_project.name}' (id: {project_id})")

            # Reload with teams
            updated_db_project = self.project_repo.get_with_teams(db, project_id)
            return self._convert_db_to_read_model(updated_db_project, db)
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

    async def request_project_access(self, db: Session, user_identifier: str, user_groups: List[str], request: ProjectAccessRequest, notifications_manager) -> ProjectAccessRequestResponse:
        """Request access to a project by sending notifications to project team members."""
        logger.debug(f"Processing project access request from user {user_identifier} for project {request.project_id}")

        # Verify project exists
        db_project = self.project_repo.get(db, request.project_id)
        if not db_project:
            raise NotFoundError(f"Project with id '{request.project_id}' not found.")

        # Check if user already has access
        if self.check_user_project_access(db, user_identifier, user_groups, request.project_id):
            raise ConflictError(f"User already has access to project '{db_project.name}'.")

        # Get all teams assigned to the project
        project_teams = self.project_repo.get_team_assignments(db, request.project_id)

        if not project_teams:
            raise ConflictError(f"Project '{db_project.name}' has no assigned teams. Cannot request access.")

        # Send notifications to all team members of assigned teams
        notifications_sent = 0

        logger.debug(f"Found {len(project_teams)} teams assigned to project '{db_project.name}'")
        for team in project_teams:
            logger.debug(f"Processing team: {team.name} (ID: {team.id})")

            # Get team with members using team repository
            team_with_members = self.team_repo.get_with_members(db, team.id)
            if not team_with_members:
                logger.warning(f"Could not fetch team {team.name} with members")
                continue

            if not team_with_members.members:
                logger.warning(f"Team {team.name} has no members, skipping notifications")
                continue

            logger.debug(f"Team {team.name} has {len(team_with_members.members)} members")
            for member in team_with_members.members:
                try:
                    logger.debug(f"Attempting to send notification to member: {member.member_identifier}")

                    # Create notification for each team member
                    notification_title = f"Project Access Request"
                    notification_description = (
                        f"User {user_identifier} is requesting access to project '{db_project.name}'"
                        f"{' - ' + request.message if request.message else ''}. "
                        f"Please contact an administrator to grant access if appropriate."
                    )

                    # Create notification using the async method
                    notification = await notifications_manager.create_notification(
                        db=db,
                        user_id=member.member_identifier,
                        title=notification_title,
                        subtitle=f"From: {user_identifier}",
                        description=notification_description,
                        link=f"/projects/{request.project_id}",
                        type=NotificationType.INFO,
                        action_type="project_access_request",
                        action_payload={
                            "project_id": request.project_id,
                            "requester": user_identifier,
                            "team_id": team.id
                        }
                    )
                    notifications_sent += 1
                    logger.debug(f"Successfully sent project access request notification to {member.member_identifier}")

                except Exception as e:
                    logger.error(f"Failed to send notification to team member {member.member_identifier}: {e}", exc_info=True)
                    continue

        if notifications_sent == 0:
            raise ConflictError(f"Could not send notifications to any team members for project '{db_project.name}'.")

        logger.info(f"Sent {notifications_sent} project access request notifications for project '{db_project.name}' from user {user_identifier}")

        return ProjectAccessRequestResponse(
            message=f"Access request sent successfully. {notifications_sent} team members have been notified.",
            project_name=db_project.name
        )

    def load_initial_data(self, db: Session) -> bool:
        """Load projects from YAML file if projects table is empty."""
        logger.debug("ProjectsManager: Checking if projects table is empty...")

        try:
            # Check if projects already exist
            existing_projects = self.project_repo.get_multi(db, limit=1)
            if existing_projects:
                logger.info("Projects table is not empty. Skipping initial data loading.")
                return False
        except Exception as e:
            logger.error(f"Error checking if projects table is empty: {e}", exc_info=True)
            return False

        # Load projects from YAML
        yaml_path = Path(__file__).parent.parent / "data" / "projects.yaml"
        if not yaml_path.exists():
            logger.info(f"Projects YAML file not found at {yaml_path}. Skipping initial data loading.")
            return False

        logger.info(f"Projects table is empty. Loading initial data from {yaml_path}...")

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'projects' not in data:
                logger.warning("No 'projects' section found in YAML file.")
                return False

            projects_data = data['projects']
            created_projects = {}  # Track project name -> project_id mapping

            # Create projects first (without team assignments)
            for project_data in projects_data:
                try:
                    # Extract project creation data (excluding assigned_teams)
                    project_create_data = {
                        'name': project_data['name'],
                        'title': project_data.get('title', ''),
                        'description': project_data.get('description', ''),
                        'tags': project_data.get('tags', []),
                        'metadata': project_data.get('metadata', {}),
                        'team_ids': []  # Will assign teams separately
                    }

                    # Resolve owner_team_name to owner_team_id if provided
                    owner_team_name = project_data.get('owner_team_name')
                    if owner_team_name:
                        owner_team_db = self.team_repo.get_by_name(db, name=owner_team_name)
                        if owner_team_db:
                            project_create_data['owner_team_id'] = owner_team_db.id
                            logger.debug(f"Resolved owner team '{owner_team_name}' to ID: {owner_team_db.id} for project '{project_data['name']}'")
                        else:
                            logger.warning(f"Owner team '{owner_team_name}' not found for project '{project_data['name']}', creating project without owner.")

                    project_create = ProjectCreate(**project_create_data)
                    created_project = self.create_project(db, project_create, current_user_id="system@startup.ucapp")
                    created_projects[project_data['name']] = created_project.id

                    logger.debug(f"Created project: {project_data['name']} with ID: {created_project.id}")

                except Exception as e:
                    logger.error(f"Error creating project '{project_data.get('name', 'unknown')}': {e}", exc_info=True)
                    continue

            # Assign teams to projects
            for project_data in projects_data:
                project_name = project_data['name']
                project_id = created_projects.get(project_name)

                if not project_id:
                    logger.warning(f"Project '{project_name}' not found in created projects, skipping team assignments.")
                    continue

                assigned_teams = project_data.get('assigned_teams', [])
                for team_name in assigned_teams:
                    try:
                        # Look up team by name
                        team_db = self.team_repo.get_by_name(db, name=team_name)
                        if not team_db:
                            logger.warning(f"Team '{team_name}' not found for project '{project_name}', skipping.")
                            continue

                        # Assign team to project
                        self.assign_team_to_project(db, project_id, team_db.id, assigned_by="system@startup.ucapp")
                        logger.debug(f"Assigned team '{team_name}' to project '{project_name}'")

                    except Exception as e:
                        logger.error(f"Error assigning team '{team_name}' to project '{project_name}': {e}", exc_info=True)
                        continue

            db.commit()
            logger.info(f"Successfully loaded {len(created_projects)} projects with team assignments from YAML file.")
            return True

        except Exception as e:
            logger.error(f"Error loading projects from YAML: {e}", exc_info=True)
            db.rollback()
            return False


# Singleton instance
projects_manager = ProjectsManager()