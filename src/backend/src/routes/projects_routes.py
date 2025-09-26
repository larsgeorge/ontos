import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.models.projects import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRead,
    ProjectSummary,
    UserProjectAccess,
    ProjectTeamAssignment,
    ProjectContext,
    ProjectAccessRequest,
    ProjectAccessRequestResponse
)
from src.controller.projects_manager import projects_manager
from src.common.database import get_db
from sqlalchemy.orm import Session
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
from src.common.dependencies import (
    DBSessionDep,
    CurrentUserDep,
    NotificationsManagerDep
)
from src.models.users import UserInfo
from src.common.errors import NotFoundError, ConflictError
from src.common.logging import get_logger

logger = get_logger(__name__)

# Define router
router = APIRouter(prefix="/api", tags=["Projects"])

# Feature ID constant
PROJECTS_FEATURE_ID = "projects"

# Project dependency
def get_projects_manager():
    return projects_manager


# Project Routes
@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def create_project(
    project_in: ProjectCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Creates a new project."""
    logger.info(f"User '{current_user.email}' attempting to create project: {project_in.name}")
    try:
        created_project = manager.create_project(db=db, project_in=project_in, current_user_id=current_user.email)
        db.commit()
        return created_project
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create project '{project_in.name}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create project: {e!s}")


@router.get(
    "/projects",
    response_model=List[ProjectRead],
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_all_projects(
    db: DBSessionDep,
    manager = Depends(get_projects_manager),
    skip: int = 0,
    limit: int = 100
):
    """Lists all projects."""
    logger.debug(f"Fetching projects (skip={skip}, limit={limit})")
    try:
        return manager.get_all_projects(db=db, skip=skip, limit=limit)
    except Exception as e:
        logger.exception(f"Failed to fetch projects: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch projects")


@router.get(
    "/projects/summary",
    response_model=List[ProjectSummary],
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_projects_summary(
    db: DBSessionDep,
    manager = Depends(get_projects_manager)
):
    """Gets a summary list of projects for dropdowns/selection."""
    logger.debug("Fetching projects summary")
    try:
        return manager.get_projects_summary(db=db)
    except Exception as e:
        logger.exception(f"Failed to fetch projects summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch projects summary")


@router.get(
    "/projects/{project_id}",
    response_model=ProjectRead,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_project(
    project_id: str,
    db: DBSessionDep,
    manager = Depends(get_projects_manager)
):
    """Gets a specific project by its ID."""
    logger.debug(f"Fetching project with id: {project_id}")
    project = manager.get_project_by_id(db=db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with id '{project_id}' not found")
    return project


@router.put(
    "/projects/{project_id}",
    response_model=ProjectRead,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Updates an existing project."""
    logger.info(f"User '{current_user.email}' attempting to update project: {project_id}")
    try:
        updated_project = manager.update_project(
            db=db,
            project_id=project_id,
            project_in=project_in,
            current_user_id=current_user.email
        )
        db.commit()
        return updated_project
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to update project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update project: {e!s}")


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.ADMIN))]
)
def delete_project(
    project_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Deletes a project. Requires Admin privileges."""
    logger.info(f"User '{current_user.email}' attempting to delete project: {project_id}")
    try:
        deleted_project = manager.delete_project(db=db, project_id=project_id)
        db.commit()
        return deleted_project
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete project: {e!s}")


# Team Assignment Routes
@router.post(
    "/projects/{project_id}/teams",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def assign_team_to_project(
    project_id: str,
    assignment: ProjectTeamAssignment,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Assigns a team to a project."""
    logger.info(f"User '{current_user.email}' assigning team {assignment.team_id} to project {project_id}")
    try:
        success = manager.assign_team_to_project(
            db=db,
            project_id=project_id,
            team_id=assignment.team_id,
            assigned_by=current_user.email
        )
        db.commit()
        return {"message": "Team assigned to project successfully"}
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to assign team to project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to assign team: {e!s}")


@router.delete(
    "/projects/{project_id}/teams/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def remove_team_from_project(
    project_id: str,
    team_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Removes a team from a project."""
    logger.info(f"User '{current_user.email}' removing team {team_id} from project {project_id}")
    try:
        success = manager.remove_team_from_project(db=db, project_id=project_id, team_id=team_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team assignment not found")
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to remove team from project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to remove team: {e!s}")


@router.get(
    "/projects/{project_id}/teams",
    response_model=List[dict],
    dependencies=[Depends(PermissionChecker(PROJECTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_project_teams(
    project_id: str,
    db: DBSessionDep,
    manager = Depends(get_projects_manager)
):
    """Gets all teams assigned to a project."""
    logger.debug(f"Fetching teams for project: {project_id}")
    try:
        return manager.get_project_teams(db=db, project_id=project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to fetch project teams: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch project teams")


# User Project Access Routes
@router.get(
    "/user/projects",
    response_model=UserProjectAccess
)
def get_user_projects(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Gets all projects that the current user has access to."""
    logger.debug(f"Fetching accessible projects for user: {current_user.email}")
    try:
        user_groups = current_user.groups or []
        return manager.get_user_projects(db=db, user_identifier=current_user.email, user_groups=user_groups)
    except Exception as e:
        logger.exception(f"Failed to fetch user projects: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch user projects")


@router.post(
    "/user/current-project",
    status_code=status.HTTP_204_NO_CONTENT
)
def set_current_project(
    project_context: ProjectContext,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_projects_manager)
):
    """Sets the current project context for the user session."""
    logger.debug(f"Setting current project {project_context.project_id} for user: {current_user.email}")
    try:
        # Verify user has access to the project if project_id is provided
        if project_context.project_id:
            user_groups = current_user.groups or []
            has_access = manager.check_user_project_access(
                db=db,
                user_identifier=current_user.email,
                user_groups=user_groups,
                project_id=project_context.project_id
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have access to this project"
                )

        # TODO: Store project context in session or user preferences
        # For now, this is a placeholder - actual implementation would depend on session management
        logger.info(f"Project context set to {project_context.project_id} for user {current_user.email}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to set current project: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set current project")


@router.post(
    "/user/request-project-access",
    response_model=ProjectAccessRequestResponse,
    status_code=status.HTTP_201_CREATED
)
async def request_project_access(
    request: ProjectAccessRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    notifications_manager: NotificationsManagerDep,
    manager = Depends(get_projects_manager)
):
    """Request access to a project by sending notifications to project team members."""
    logger.info(f"User '{current_user.email}' requesting access to project: {request.project_id}")
    try:
        user_groups = current_user.groups or []
        response = await manager.request_project_access(
            db=db,
            user_identifier=current_user.email,
            user_groups=user_groups,
            request=request,
            notifications_manager=notifications_manager
        )
        db.commit()
        return response
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to request project access: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to request project access: {e!s}")


def register_routes(app):
    app.include_router(router)
    logger.info("Projects routes registered with prefix /api/projects")