from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, validator, field_validator
import json # For parsing stringified lists

# --- Base Model --- #
class DataDomainBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the data domain.")
    description: Optional[str] = Field(None, description="Optional description for the domain.")
    owner: List[str] = Field(..., min_items=1, description="List of owners (principals - users/groups) for the domain.")
    tags: Optional[List[str]] = Field(None, description="Optional list of tags associated with the domain.")

    @validator('owner', 'tags', pre=True, each_item=True)
    def check_string_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("Owner and tag strings cannot be empty")
        return v

# --- Create Model --- #
class DataDomainCreate(DataDomainBase):
    # No extra fields needed for creation beyond Base + who is creating it (captured in manager)
    pass

# --- Update Model --- #
class DataDomainUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="New name for the data domain.")
    description: Optional[str] = Field(None, description="New description for the domain.")
    owner: Optional[List[str]] = Field(None, min_items=1, description="New list of owners for the domain.")
    tags: Optional[List[str]] = Field(None, description="New list of tags for the domain.")

    @validator('owner', 'tags', pre=True, each_item=True)
    def check_update_string_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError("Owner and tag strings cannot be empty")
        return v

# --- Read Model (includes DB fields) --- #
class DataDomainRead(DataDomainBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: str

    # Validator to parse stringified list from DB before standard validation
    @field_validator('owner', 'tags', mode='before')
    def parse_stringified_list(cls, value):
        if value is None: 
            return None # Allow optional tags to be None
        if isinstance(value, str):
            try:
                # Attempt to parse the string as a JSON list
                parsed_value = json.loads(value.replace("'", '"')) # Replace single quotes for valid JSON
                if not isinstance(parsed_value, list):
                     raise ValueError("Parsed value is not a list")
                # Further check if items in list are strings?
                if not all(isinstance(item, str) for item in parsed_value):
                     raise ValueError("Not all items in parsed list are strings")
                # Optional: Validate non-empty strings within the list here if desired
                # if any(not item.strip() for item in parsed_value):
                #      raise ValueError("List items cannot be empty strings")
                return parsed_value
            except (json.JSONDecodeError, ValueError) as e:
                # Handle cases where the string is not a valid JSON list representation
                # Or if post-parsing validation fails
                # Depending on requirements, you might raise, return default, or attempt other parsing
                print(f"Warning: Could not parse string '{value}' as list: {e}. Returning empty list.")
                # Decide recovery strategy: return empty list, None, or raise error
                # Returning empty list might hide data issues but prevent app crash
                return [] # Or raise ValueError(f"Invalid list format: {value}")
        # If it's already a list (or None), pass it through
        if isinstance(value, list):
             return value
        # Handle unexpected types
        raise ValueError(f"Unexpected type for list field: {type(value)}")

    class Config:
        from_attributes = True # Pydantic v2 config for ORM mode 