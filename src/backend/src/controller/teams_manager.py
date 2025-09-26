import logging
import json
import yaml
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.repositories.teams_repository import team_repo, team_member_repo
from src.models.teams import (
    TeamCreate,
    TeamUpdate,
    TeamRead,
    TeamSummary,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberRead
)
from src.db_models.teams import TeamDb, TeamMemberDb
from src.common.logging import get_logger
from src.common.errors import ConflictError, NotFoundError

logger = get_logger(__name__)


class TeamsManager:
    def __init__(self):
        self.team_repo = team_repo
        self.team_member_repo = team_member_repo
        logger.debug("TeamsManager initialized.")

    def _serialize_list_fields(self, data: dict) -> dict:
        """Helper to serialize list fields to JSON strings for database storage."""
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = json.dumps(data['tags'])
        if 'metadata' in data and isinstance(data['metadata'], dict):
            data['metadata'] = json.dumps(data['metadata'])
        return data

    def _convert_db_to_read_model(self, db_team: TeamDb) -> TeamRead:
        """Helper to convert DB model to Read model."""
        return TeamRead.model_validate(db_team)

    def _convert_db_to_summary_model(self, db_team: TeamDb) -> TeamSummary:
        """Helper to convert DB model to Summary model."""
        return TeamSummary(
            id=db_team.id,
            name=db_team.name,
            title=db_team.title,
            domain_id=db_team.domain_id,
            member_count=len(db_team.members) if db_team.members else 0
        )

    # Team CRUD operations
    def create_team(self, db: Session, team_in: TeamCreate, current_user_id: str) -> TeamRead:
        """Creates a new team."""
        logger.debug(f"Attempting to create team: {team_in.name}")

        # Check if team name already exists
        existing_team = self.team_repo.get_by_name(db, name=team_in.name)
        if existing_team:
            raise ConflictError(f"Team with name '{team_in.name}' already exists.")

        # Prepare data for database
        db_obj_data = team_in.model_dump(exclude_unset=True)
        db_obj_data['created_by'] = current_user_id
        db_obj_data['updated_by'] = current_user_id
        self._serialize_list_fields(db_obj_data)

        db_team = TeamDb(**db_obj_data)

        try:
            db.add(db_team)
            db.flush()
            db.refresh(db_team)
            logger.info(f"Successfully created team '{db_team.name}' with id: {db_team.id}")
            return self._convert_db_to_read_model(db_team)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating team '{team_in.name}': {e}")
            if "unique constraint" in str(e).lower():
                raise ConflictError(f"Team with name '{team_in.name}' already exists.")
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error creating team '{team_in.name}': {e}")
            raise

    def get_team_by_id(self, db: Session, team_id: str) -> Optional[TeamRead]:
        """Gets a team by its ID, including members."""
        logger.debug(f"Fetching team with id: {team_id}")
        db_team = self.team_repo.get_with_members(db, team_id)
        if not db_team:
            return None
        return self._convert_db_to_read_model(db_team)

    def get_all_teams(self, db: Session, skip: int = 0, limit: int = 100, domain_id: Optional[str] = None) -> List[TeamRead]:
        """Gets a list of all teams, optionally filtered by domain."""
        logger.debug(f"Fetching teams with skip={skip}, limit={limit}, domain_id={domain_id}")
        db_teams = self.team_repo.get_multi_with_members(db, skip=skip, limit=limit, domain_id=domain_id)
        return [self._convert_db_to_read_model(team) for team in db_teams]

    def get_teams_summary(self, db: Session, domain_id: Optional[str] = None) -> List[TeamSummary]:
        """Gets a summary list of teams for dropdowns/selection."""
        logger.debug(f"Fetching teams summary for domain_id={domain_id}")
        db_teams = self.team_repo.get_multi_with_members(db, limit=1000, domain_id=domain_id)
        return [self._convert_db_to_summary_model(team) for team in db_teams]

    def get_teams_by_domain(self, db: Session, domain_id: str) -> List[TeamRead]:
        """Gets all teams belonging to a specific domain."""
        db_teams = self.team_repo.get_teams_by_domain(db, domain_id)
        return [self._convert_db_to_read_model(team) for team in db_teams]

    def get_standalone_teams(self, db: Session) -> List[TeamRead]:
        """Gets all standalone teams (not assigned to a domain)."""
        db_teams = self.team_repo.get_standalone_teams(db)
        return [self._convert_db_to_read_model(team) for team in db_teams]

    def get_teams_for_user(self, db: Session, user_identifier: str) -> List[TeamRead]:
        """Gets all teams where a user is a member."""
        db_teams = self.team_repo.get_teams_for_user(db, user_identifier)
        return [self._convert_db_to_read_model(team) for team in db_teams]

    def update_team(self, db: Session, team_id: str, team_in: TeamUpdate, current_user_id: str) -> Optional[TeamRead]:
        """Updates an existing team."""
        logger.debug(f"Attempting to update team with id: {team_id}")

        db_team = self.team_repo.get(db, team_id)
        if not db_team:
            raise NotFoundError(f"Team with id '{team_id}' not found.")

        # Check for name conflicts if name is being updated
        if team_in.name and team_in.name != db_team.name:
            existing_team = self.team_repo.get_by_name(db, name=team_in.name)
            if existing_team:
                raise ConflictError(f"Team with name '{team_in.name}' already exists.")

        update_data = team_in.model_dump(exclude_unset=True)
        update_data['updated_by'] = current_user_id
        self._serialize_list_fields(update_data)

        try:
            updated_db_team = self.team_repo.update(db=db, db_obj=db_team, obj_in=update_data)
            db.flush()
            db.refresh(updated_db_team)
            logger.info(f"Successfully updated team '{updated_db_team.name}' (id: {team_id})")
            return self._convert_db_to_read_model(updated_db_team)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error updating team {team_id}: {e}")
            if "unique constraint" in str(e).lower():
                raise ConflictError(f"Team name '{team_in.name}' is already in use.")
            raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error updating team {team_id}: {e}")
            raise

    def delete_team(self, db: Session, team_id: str) -> Optional[TeamRead]:
        """Deletes a team by its ID."""
        logger.debug(f"Attempting to delete team with id: {team_id}")

        db_team = self.team_repo.get_with_members(db, team_id)
        if not db_team:
            raise NotFoundError(f"Team with id '{team_id}' not found.")

        read_model = self._convert_db_to_read_model(db_team)

        try:
            self.team_repo.remove(db=db, id=team_id)
            logger.info(f"Successfully deleted team '{read_model.name}' (id: {team_id})")
            return read_model
        except Exception as e:
            db.rollback()
            logger.exception(f"Error deleting team {team_id}: {e}")
            raise

    # Team Member operations
    def add_team_member(self, db: Session, team_id: str, member_in: TeamMemberCreate, current_user_id: str) -> TeamMemberRead:
        """Adds a member to a team."""
        logger.debug(f"Adding member {member_in.member_identifier} to team {team_id}")

        # Check if team exists
        db_team = self.team_repo.get(db, team_id)
        if not db_team:
            raise NotFoundError(f"Team with id '{team_id}' not found.")

        # Check if member already exists
        existing_member = self.team_member_repo.get_by_team_and_member(
            db, team_id=team_id, member_identifier=member_in.member_identifier
        )
        if existing_member:
            raise ConflictError(f"Member '{member_in.member_identifier}' is already in team '{db_team.name}'.")

        db_obj_data = member_in.model_dump()
        db_obj_data['team_id'] = team_id
        db_obj_data['added_by'] = current_user_id

        db_member = TeamMemberDb(**db_obj_data)

        try:
            db.add(db_member)
            db.flush()
            db.refresh(db_member)
            logger.info(f"Successfully added member '{member_in.member_identifier}' to team '{db_team.name}'")
            return TeamMemberRead.model_validate(db_member)
        except Exception as e:
            db.rollback()
            logger.exception(f"Error adding member to team: {e}")
            raise

    def update_team_member(self, db: Session, team_id: str, member_id: str, member_in: TeamMemberUpdate, current_user_id: str) -> Optional[TeamMemberRead]:
        """Updates a team member."""
        logger.debug(f"Updating team member {member_id} in team {team_id}")

        db_member = self.team_member_repo.get(db, member_id)
        if not db_member or db_member.team_id != team_id:
            raise NotFoundError(f"Team member with id '{member_id}' not found in team '{team_id}'.")

        update_data = member_in.model_dump(exclude_unset=True)

        try:
            updated_db_member = self.team_member_repo.update(db=db, db_obj=db_member, obj_in=update_data)
            db.flush()
            db.refresh(updated_db_member)
            logger.info(f"Successfully updated team member '{updated_db_member.member_identifier}'")
            return TeamMemberRead.model_validate(updated_db_member)
        except Exception as e:
            db.rollback()
            logger.exception(f"Error updating team member: {e}")
            raise

    def remove_team_member(self, db: Session, team_id: str, member_identifier: str) -> bool:
        """Removes a member from a team."""
        logger.debug(f"Removing member {member_identifier} from team {team_id}")

        try:
            removed_member = self.team_member_repo.remove_by_team_and_member(
                db, team_id=team_id, member_identifier=member_identifier
            )
            if removed_member:
                logger.info(f"Successfully removed member '{member_identifier}' from team")
                return True
            else:
                logger.warning(f"Member '{member_identifier}' not found in team '{team_id}'")
                return False
        except Exception as e:
            db.rollback()
            logger.exception(f"Error removing team member: {e}")
            raise

    def get_team_members(self, db: Session, team_id: str) -> List[TeamMemberRead]:
        """Gets all members of a team."""
        db_members = self.team_member_repo.get_members_by_team(db, team_id)
        return [TeamMemberRead.model_validate(member) for member in db_members]

    def load_initial_data(self, db: Session) -> bool:
        """Load teams from YAML file if teams table is empty."""
        logger.debug("TeamsManager: Checking if teams table is empty...")

        try:
            # Check if teams already exist
            existing_teams = self.team_repo.get_multi(db, limit=1)
            if existing_teams:
                logger.info("Teams table is not empty. Skipping initial data loading.")
                return False
        except Exception as e:
            logger.error(f"Error checking if teams table is empty: {e}", exc_info=True)
            return False

        # Load teams from YAML
        yaml_path = Path(__file__).parent.parent / "data" / "teams.yaml"
        if not yaml_path.exists():
            logger.info(f"Teams YAML file not found at {yaml_path}. Skipping initial data loading.")
            return False

        logger.info(f"Teams table is empty. Loading initial data from {yaml_path}...")

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'teams' not in data:
                logger.warning("No 'teams' section found in YAML file.")
                return False

            teams_data = data['teams']
            created_teams = {}  # Track team name -> team_id mapping

            # Create teams first (without members)
            for team_data in teams_data:
                try:
                    # Extract team creation data (excluding members)
                    team_create_data = {
                        'name': team_data['name'],
                        'title': team_data.get('title', ''),
                        'description': team_data.get('description', ''),
                        'domain_id': team_data.get('domain_id'),
                        'tags': team_data.get('tags', []),
                        'metadata': team_data.get('metadata', {})
                    }

                    team_create = TeamCreate(**team_create_data)
                    created_team = self.create_team(db, team_create, current_user_id="system@startup.ucapp")
                    created_teams[team_data['name']] = created_team.id

                    logger.debug(f"Created team: {team_data['name']} with ID: {created_team.id}")

                except Exception as e:
                    logger.error(f"Error creating team '{team_data.get('name', 'unknown')}': {e}", exc_info=True)
                    continue

            # Add members to teams
            for team_data in teams_data:
                team_name = team_data['name']
                team_id = created_teams.get(team_name)

                if not team_id:
                    logger.warning(f"Team '{team_name}' not found in created teams, skipping members.")
                    continue

                members_data = team_data.get('members', [])
                for member_data in members_data:
                    try:
                        member_create = TeamMemberCreate(
                            member_type=member_data['member_type'],
                            member_identifier=member_data['member_identifier'],
                            app_role_override=member_data.get('app_role_override')
                        )

                        self.add_team_member(db, team_id, member_create, current_user_id="system@startup.ucapp")
                        logger.debug(f"Added member {member_data['member_identifier']} to team {team_name}")

                    except Exception as e:
                        logger.error(f"Error adding member {member_data.get('member_identifier', 'unknown')} to team {team_name}: {e}", exc_info=True)
                        continue

            db.commit()
            logger.info(f"Successfully loaded {len(created_teams)} teams with members from YAML file.")
            return True

        except Exception as e:
            logger.error(f"Error loading teams from YAML: {e}", exc_info=True)
            db.rollback()
            return False


# Singleton instance
teams_manager = TeamsManager()