from src.common.repository import CRUDBase
from src.db_models.projects import ProjectDb, project_team_association
from src.db_models.teams import TeamDb
from src.models.projects import ProjectCreate, ProjectUpdate
from src.common.logging import get_logger
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, delete, or_
from typing import List, Optional

logger = get_logger(__name__)


class ProjectRepository(CRUDBase[ProjectDb, ProjectCreate, ProjectUpdate]):
    def __init__(self):
        super().__init__(ProjectDb)
        logger.info("ProjectRepository initialized.")

    def get_with_teams(self, db: Session, id: str) -> Optional[ProjectDb]:
        """Gets a single project by ID, eager loading teams and owner team."""
        logger.debug(f"Fetching {self.model.__name__} with teams for id: {id}")
        try:
            return (
                db.query(self.model)
                .options(selectinload(self.model.teams))
                .options(selectinload(self.model.owner_team))
                .filter(self.model.id == id)
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} with teams by id {id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_multi_with_teams(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ProjectDb]:
        """Gets multiple projects, eager loading teams and owner teams."""
        logger.debug(f"Fetching multiple {self.model.__name__} with teams, skip={skip}, limit={limit}")
        try:
            return (
                db.query(self.model)
                .options(selectinload(self.model.teams))
                .options(selectinload(self.model.owner_team))
                .order_by(self.model.name)
                .offset(skip)
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching multiple {self.model.__name__} with teams: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_name(self, db: Session, *, name: str) -> Optional[ProjectDb]:
        """Gets a project by name."""
        logger.debug(f"Fetching {self.model.__name__} with name: {name}")
        try:
            return db.query(self.model).filter(self.model.name == name).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching {self.model.__name__} by name {name}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_projects_for_user(self, db: Session, user_identifier: str, user_groups: List[str]) -> List[ProjectDb]:
        """Gets all projects that a user has access to through team membership."""
        logger.debug(f"Fetching projects for user: {user_identifier}")
        try:
            # Get projects where user is a team member (either directly or via group)
            from src.db_models.teams import TeamMemberDb

            # Build filter for user identifier and groups
            member_filters = [TeamMemberDb.member_identifier == user_identifier]
            for group in user_groups:
                member_filters.append(TeamMemberDb.member_identifier == group)

            return (
                db.query(self.model)
                .options(selectinload(self.model.teams))
                .options(selectinload(self.model.owner_team))
                .join(project_team_association)
                .join(TeamDb)
                .join(TeamMemberDb)
                .filter(
                    and_(
                        project_team_association.c.project_id == self.model.id,
                        project_team_association.c.team_id == TeamDb.id,
                        TeamMemberDb.team_id == TeamDb.id,
                        or_(*member_filters)
                    )
                )
                .distinct()
                .order_by(self.model.name)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching projects for user {user_identifier}: {e}", exc_info=True)
            db.rollback()
            raise

    def assign_team(self, db: Session, *, project_id: str, team_id: str, assigned_by: str) -> bool:
        """Assigns a team to a project."""
        logger.debug(f"Assigning team {team_id} to project {project_id}")
        try:
            # Check if assignment already exists
            existing = (
                db.query(project_team_association)
                .filter(
                    and_(
                        project_team_association.c.project_id == project_id,
                        project_team_association.c.team_id == team_id
                    )
                )
                .first()
            )

            if existing:
                logger.warning(f"Team {team_id} is already assigned to project {project_id}")
                return False

            # Create new assignment
            from sqlalchemy import insert
            stmt = insert(project_team_association).values(
                project_id=project_id,
                team_id=team_id,
                assigned_by=assigned_by
            )
            db.execute(stmt)
            db.flush()
            logger.info(f"Successfully assigned team {team_id} to project {project_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error assigning team to project: {e}", exc_info=True)
            db.rollback()
            raise

    def remove_team(self, db: Session, *, project_id: str, team_id: str) -> bool:
        """Removes a team from a project."""
        logger.debug(f"Removing team {team_id} from project {project_id}")
        try:
            stmt = delete(project_team_association).where(
                and_(
                    project_team_association.c.project_id == project_id,
                    project_team_association.c.team_id == team_id
                )
            )
            result = db.execute(stmt)
            db.flush()

            if result.rowcount > 0:
                logger.info(f"Successfully removed team {team_id} from project {project_id}")
                return True
            else:
                logger.warning(f"No assignment found for team {team_id} in project {project_id}")
                return False
        except SQLAlchemyError as e:
            logger.error(f"Database error removing team from project: {e}", exc_info=True)
            db.rollback()
            raise

    def get_team_assignments(self, db: Session, project_id: str) -> List[TeamDb]:
        """Gets all teams assigned to a project."""
        logger.debug(f"Fetching team assignments for project: {project_id}")
        try:
            return (
                db.query(TeamDb)
                .join(project_team_association)
                .filter(project_team_association.c.project_id == project_id)
                .order_by(TeamDb.name)
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching team assignments for project {project_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_projects_by_domain_relationship(
        self, db: Session, user_identifier: str, user_groups: List[str]
    ) -> List[ProjectDb]:
        """Gets projects visible to user based on domain relationships.
        
        Returns projects where:
        - User's teams share a domain with the project's owner team
        - Projects with no domain association (considered public)
        - Projects user is already a member of
        """
        logger.debug(f"Fetching domain-related projects for user: {user_identifier}")
        try:
            from src.db_models.teams import TeamMemberDb
            from src.db_models.data_domains import DataDomain
            
            # Get user's team IDs
            member_filters = [TeamMemberDb.member_identifier == user_identifier]
            for group in user_groups:
                member_filters.append(TeamMemberDb.member_identifier == group)
            
            user_team_ids_query = (
                db.query(TeamDb.id)
                .join(TeamMemberDb)
                .filter(or_(*member_filters))
                .distinct()
            )
            user_team_ids = [tid[0] for tid in user_team_ids_query.all()]
            
            if not user_team_ids:
                # User not in any team, only show projects with no domain
                return (
                    db.query(self.model)
                    .options(selectinload(self.model.teams))
                    .options(selectinload(self.model.owner_team))
                    .join(TeamDb, self.model.owner_team_id == TeamDb.id, isouter=True)
                    .filter(
                        or_(
                            TeamDb.domain_id.is_(None),
                            self.model.owner_team_id.is_(None)
                        )
                    )
                    .distinct()
                    .order_by(self.model.name)
                    .all()
                )
            
            # Get domains of user's teams
            user_domain_ids_query = (
                db.query(TeamDb.domain_id)
                .filter(TeamDb.id.in_(user_team_ids))
                .filter(TeamDb.domain_id.isnot(None))
                .distinct()
            )
            user_domain_ids = [did[0] for did in user_domain_ids_query.all()]
            
            # Build filter conditions
            visibility_filters = [
                # Projects with no domain (public)
                TeamDb.domain_id.is_(None),
                # Projects user is already a member of
                project_team_association.c.team_id.in_(user_team_ids),
            ]
            
            # Projects in same domains as user's teams
            if user_domain_ids:
                visibility_filters.append(TeamDb.domain_id.in_(user_domain_ids))
            
            return (
                db.query(self.model)
                .options(selectinload(self.model.teams))
                .options(selectinload(self.model.owner_team))
                .outerjoin(TeamDb, self.model.owner_team_id == TeamDb.id)
                .outerjoin(
                    project_team_association,
                    project_team_association.c.project_id == self.model.id
                )
                .filter(or_(*visibility_filters))
                .distinct()
                .order_by(self.model.name)
                .all()
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching domain-related projects: {e}", exc_info=True)
            db.rollback()
            raise


# Singleton instance
project_repo = ProjectRepository()