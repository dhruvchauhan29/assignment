"""
Project Pydantic schemas.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    name: str
    description: Optional[str] = None
    product_request: str

    @field_validator('product_request')
    @classmethod
    def validate_product_request(cls, v: str) -> str:
        """Validate that product_request is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError('Product Request cannot be empty or whitespace-only')
        return v.strip()


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    product_request: Optional[str] = None

    @field_validator('product_request')
    @classmethod
    def validate_product_request(cls, v: Optional[str]) -> Optional[str]:
        """Validate that product_request is not empty or whitespace-only if provided."""
        if v is not None and not v.strip():
            raise ValueError('Product Request cannot be empty or whitespace-only')
        return v.strip() if v else None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: int
    name: str
    description: Optional[str]
    product_request: str
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
