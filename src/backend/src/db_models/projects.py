from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.common.database import Base


# Association table for many-to-many relationship between projects and teams
project_team_association = Table(
    'project_teams', Base.metadata,
    Column('project_id', String, ForeignKey('projects.id'), primary_key=True),
    Column('team_id', String, ForeignKey('teams.id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', String, nullable=False)  # User who made the assignment
)


class ProjectDb(Base):
    """SQLAlchemy model for Projects"""
    __tablename__ = 'projects'

    # Core Fields
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Metadata fields (stored as JSON strings)
    tags = Column(String, nullable=True, default='[]')  # JSON array of tags
    extra_metadata = Column(String, nullable=True, default='{}')  # JSON object for links, images, etc.

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False)  # User email/ID
    updated_by = Column(String, nullable=False)  # User email/ID

    # Relationships
    teams = relationship("TeamDb", secondary=project_team_association, lazy="selectin")

    def __repr__(self):
        return f"<ProjectDb(id='{self.id}', name='{self.name}')>"


