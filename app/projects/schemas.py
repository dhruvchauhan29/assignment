"""
Project Pydantic schemas.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    name: str
    description: Optional[str] = None
    product_request: str
    documents: Optional[List[str]] = None  # List of document file paths/URLs
    
    @field_validator('product_request')
    @classmethod
    def validate_product_request(cls, v):
        """Validate product request is not empty."""
        if not v or not v.strip():
            raise ValueError('Product request cannot be empty')
        return v.strip()


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    product_request: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: int
    name: str
    description: Optional[str]
    product_request: str
    documents: Optional[List[dict]] = None
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
