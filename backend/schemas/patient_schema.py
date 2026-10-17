"""
Patient Profile Request and Response Schemas.

Enforces HIPAA de-identification rules, ensuring patient codes are unique
and external medical record numbers are never stored in plaintext.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PatientCreateSchema(BaseModel):
    """Payload for creating a new de-identified patient record."""
    age: int = Field(..., ge=0, le=130, description="Patient age in years")
    sex: str = Field(..., description="Biological sex ('Male' or 'Female')")
    medical_record_number: Optional[str] = Field(
        default=None,
        description="External MRN. Converted to a one-way SHA-256 hash before storage.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000, description="De-identified clinical intake notes")

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str) -> str:
        clean = v.strip().capitalize()
        if clean not in ("Male", "Female"):
            raise ValueError("Sex must be either 'Male' or 'Female'.")
        return clean


class PatientUpdateSchema(BaseModel):
    """Payload for updating an existing patient record."""
    age: Optional[int] = Field(default=None, ge=0, le=130)
    sex: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().capitalize()
        if clean not in ("Male", "Female"):
            raise ValueError("Sex must be either 'Male' or 'Female'.")
        return clean


class PatientResponseSchema(BaseModel):
    """Detailed patient representation."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_code: str
    age: int
    sex: str
    is_active: bool
    notes: Optional[str] = None
    assessments_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
