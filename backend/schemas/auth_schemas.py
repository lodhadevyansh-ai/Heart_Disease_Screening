"""
Authentication and Authorization Request/Response Schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequestSchema(BaseModel):
    """Credentials payload for JWT generation."""
    username: str = Field(..., min_length=3, max_length=64, description="User account identifier")
    password: str = Field(..., min_length=6, max_length=128, description="User password")


class UserProfileSchema(BaseModel):
    """User profile data returned in token payload and /me endpoint."""
    id: int
    username: str
    role: str
    name: str
    email: Optional[str] = None
    patient_id: Optional[int] = None


class TokenResponseSchema(BaseModel):
    """JWT response payload."""
    access_token: str
    token_type: str = "Bearer"
    expires_in_hours: int
    user: UserProfileSchema
