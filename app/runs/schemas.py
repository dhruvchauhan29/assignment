"""
Run Pydantic schemas.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


class RunCreate(BaseModel):
    """Schema for creating a run."""
    project_id: int


class RunResponse(BaseModel):
    """Schema for run response."""
    id: int
    project_id: int
    status: str
    current_stage: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

    class Config:
        from_attributes = True


class ArtifactResponse(BaseModel):
    """Schema for artifact response."""
    id: int
    run_id: int
    artifact_type: str
    name: str
    content: str
    artifact_metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalCreate(BaseModel):
    """Schema for creating/updating approval."""
    approved: bool
    feedback: Optional[str] = None
    action: Optional[str] = "proceed"  # "proceed", "regenerate", "reject"

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate action is one of the allowed values."""
        valid_actions = ["proceed", "regenerate", "reject"]
        if v and v not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v or "proceed"


class ApprovalResponse(BaseModel):
    """Schema for approval response."""
    id: int
    run_id: int
    stage: str
    approved: Optional[bool]
    feedback: Optional[str]
    action: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    """Schema for SSE progress updates."""
    run_id: int
    stage: str
    message: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class RunStatusResponse(BaseModel):
    """Schema for run status response."""
    run_id: int
    status: str
    current_stage: str

    class Config:
        from_attributes = True
