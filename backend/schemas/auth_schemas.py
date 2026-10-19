"""
Authentication and Authorization Request/Response Schemas.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class LoginRequestSchema(BaseModel):
    """Credentials payload for JWT generation."""
    username: str = Field(..., min_length=3, max_length=120, description="User account identifier or email")
    password: str = Field(..., min_length=6, max_length=128, description="User password")


class RegisterRequestSchema(BaseModel):
    """Account registration payload."""
    full_name: str = Field(..., min_length=2, max_length=120, description="Full name of the user")
    email: str = Field(..., min_length=5, max_length=120, description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 chars)")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Password confirmation")
    role: Optional[str] = Field("patient", description="Account role: patient or clinician")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        norm = (v or "").strip().lower()
        if not EMAIL_REGEX.match(norm):
            raise ValueError("Invalid email format. Please provide a valid email address.")
        return norm

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number.")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match. Please verify your password confirmation.")
        return self


class DeleteAccountRequestSchema(BaseModel):
    """Reauthentication payload for permanent account deletion."""
    password: str = Field(..., min_length=1, max_length=128, description="Current password for reauthentication")


class UserProfileSchema(BaseModel):
    """User profile data returned in token payload and /me endpoint."""
    id: int
    full_name: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: str
    name: Optional[str] = None
    patient_id: Optional[int] = None
    created_at: Optional[str] = None


class TokenResponseSchema(BaseModel):
    """JWT response payload."""
    access_token: str
    token_type: str = "Bearer"
    expires_in_hours: int
    user: UserProfileSchema
