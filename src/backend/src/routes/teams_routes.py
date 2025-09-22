import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.models.teams import (
    TeamCreate,
    TeamUpdate,
    TeamRead,
    TeamSummary,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberRead
)
from src.controller.teams_manager import teams_manager
from src.common.database import get_db
from sqlalchemy.orm import Session
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
from src.common.dependencies import (
    DBSessionDep,
    CurrentUserDep
)
from src.models.users import UserInfo
from src.common.errors import NotFoundError, ConflictError
from src.common.logging import get_logger

logger = get_logger(__name__)

# Define router
router = APIRouter(prefix="/api", tags=["Teams"])

# Feature ID constant
TEAMS_FEATURE_ID = "teams"

# Team dependency
def get_teams_manager():
    return teams_manager


# Team Routes
@router.post(
    "/teams",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def create_team(
    team_in: TeamCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Creates a new team."""
    logger.info(f"User '{current_user.email}' attempting to create team: {team_in.name}")
    try:
        created_team = manager.create_team(db=db, team_in=team_in, current_user_id=current_user.email)
        db.commit()
        return created_team
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create team '{team_in.name}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create team: {e!s}")


@router.get(
    "/teams",
    response_model=List[TeamRead],
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_all_teams(
    db: DBSessionDep,
    manager = Depends(get_teams_manager),
    skip: int = 0,
    limit: int = 100,
    domain_id: Optional[str] = Query(None, description="Filter teams by domain ID")
):
    """Lists all teams, optionally filtered by domain."""
    logger.debug(f"Fetching teams (skip={skip}, limit={limit}, domain_id={domain_id})")
    try:
        return manager.get_all_teams(db=db, skip=skip, limit=limit, domain_id=domain_id)
    except Exception as e:
        logger.exception(f"Failed to fetch teams: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch teams")


@router.get(
    "/teams/summary",
    response_model=List[TeamSummary],
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_teams_summary(
    db: DBSessionDep,
    manager = Depends(get_teams_manager),
    domain_id: Optional[str] = Query(None, description="Filter teams by domain ID")
):
    """Gets a summary list of teams for dropdowns/selection."""
    logger.debug(f"Fetching teams summary for domain_id={domain_id}")
    try:
        return manager.get_teams_summary(db=db, domain_id=domain_id)
    except Exception as e:
        logger.exception(f"Failed to fetch teams summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch teams summary")


@router.get(
    "/teams/{team_id}",
    response_model=TeamRead,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_team(
    team_id: str,
    db: DBSessionDep,
    manager = Depends(get_teams_manager)
):
    """Gets a specific team by its ID."""
    logger.debug(f"Fetching team with id: {team_id}")
    team = manager.get_team_by_id(db=db, team_id=team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team with id '{team_id}' not found")
    return team


@router.put(
    "/teams/{team_id}",
    response_model=TeamRead,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def update_team(
    team_id: str,
    team_in: TeamUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Updates an existing team."""
    logger.info(f"User '{current_user.email}' attempting to update team: {team_id}")
    try:
        updated_team = manager.update_team(
            db=db,
            team_id=team_id,
            team_in=team_in,
            current_user_id=current_user.email
        )
        db.commit()
        return updated_team
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to update team {team_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update team: {e!s}")


@router.delete(
    "/teams/{team_id}",
    response_model=TeamRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.ADMIN))]
)
def delete_team(
    team_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Deletes a team. Requires Admin privileges."""
    logger.info(f"User '{current_user.email}' attempting to delete team: {team_id}")
    try:
        deleted_team = manager.delete_team(db=db, team_id=team_id)
        db.commit()
        return deleted_team
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to delete team {team_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete team: {e!s}")


# Team Member Routes
@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def add_team_member(
    team_id: str,
    member_in: TeamMemberCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Adds a member to a team."""
    logger.info(f"User '{current_user.email}' adding member {member_in.member_identifier} to team {team_id}")
    try:
        member = manager.add_team_member(
            db=db,
            team_id=team_id,
            member_in=member_in,
            current_user_id=current_user.email
        )
        db.commit()
        return member
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to add member to team: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add team member: {e!s}")


@router.get(
    "/teams/{team_id}/members",
    response_model=List[TeamMemberRead],
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_team_members(
    team_id: str,
    db: DBSessionDep,
    manager = Depends(get_teams_manager)
):
    """Gets all members of a team."""
    logger.debug(f"Fetching members for team: {team_id}")
    try:
        return manager.get_team_members(db=db, team_id=team_id)
    except Exception as e:
        logger.exception(f"Failed to fetch team members: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch team members")


@router.put(
    "/teams/{team_id}/members/{member_id}",
    response_model=TeamMemberRead,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def update_team_member(
    team_id: str,
    member_id: str,
    member_in: TeamMemberUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Updates a team member."""
    logger.info(f"User '{current_user.email}' updating team member {member_id} in team {team_id}")
    try:
        updated_member = manager.update_team_member(
            db=db,
            team_id=team_id,
            member_id=member_id,
            member_in=member_in,
            current_user_id=current_user.email
        )
        db.commit()
        return updated_member
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to update team member: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update team member: {e!s}")


@router.delete(
    "/teams/{team_id}/members/{member_identifier}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def remove_team_member(
    team_id: str,
    member_identifier: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager = Depends(get_teams_manager)
):
    """Removes a member from a team."""
    logger.info(f"User '{current_user.email}' removing member {member_identifier} from team {team_id}")
    try:
        success = manager.remove_team_member(db=db, team_id=team_id, member_identifier=member_identifier)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Member '{member_identifier}' not found in team")
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to remove team member: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to remove team member: {e!s}")


# Domain-specific routes
@router.get(
    "/domains/{domain_id}/teams",
    response_model=List[TeamRead],
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_teams_by_domain(
    domain_id: str,
    db: DBSessionDep,
    manager = Depends(get_teams_manager)
):
    """Gets all teams belonging to a specific domain."""
    logger.debug(f"Fetching teams for domain: {domain_id}")
    try:
        return manager.get_teams_by_domain(db=db, domain_id=domain_id)
    except Exception as e:
        logger.exception(f"Failed to fetch teams for domain: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch teams for domain")


@router.get(
    "/teams/standalone",
    response_model=List[TeamRead],
    dependencies=[Depends(PermissionChecker(TEAMS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_standalone_teams(
    db: DBSessionDep,
    manager = Depends(get_teams_manager)
):
    """Gets all standalone teams (not assigned to a domain)."""
    logger.debug("Fetching standalone teams")
    try:
        return manager.get_standalone_teams(db=db)
    except Exception as e:
        logger.exception(f"Failed to fetch standalone teams: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch standalone teams")


def register_routes(app):
    app.include_router(router)
    logger.info("Teams routes registered with prefix /api/teams")