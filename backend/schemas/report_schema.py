"""
Clinical Document Metadata and Structured Laboratory Measurement Schemas.

CRITICAL RULES:
1. File metadata is tracked independently of clinical data extraction.
2. Uploaded documents are NOT claimed to be interpreted automatically.
3. Structured lab measurements distinguish missing values from 0.0.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponseSchema(BaseModel):
    """Metadata response for an uploaded clinical file."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    original_filename: str
    stored_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    document_category: str
    parsing_status: str
    is_verified_by_clinician: bool
    uploaded_at: Optional[str] = None
    extraction_notice: str = (
        "Document securely stored outside public directory. "
        "No automated diagnostic interpretation performed on unverified raw files."
    )


class StructuredLabCreateSchema(BaseModel):
    """Payload to record a structured clinical lab measurement."""
    test_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Standardized lab test name (e.g., 'cholesterol', 'serum_creatinine', 'ejection_fraction', 'troponin_i')",
    )
    value_numeric: Optional[float] = Field(
        default=None,
        description="Numeric measurement value. Missing values must be None, never 0.0.",
    )
    value_text: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Qualitative result (e.g., 'negative', '<0.01', 'normal')",
    )
    unit: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Measurement unit (e.g. 'mg/dL', '%', 'pg/mL')",
    )
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    flag: Optional[str] = Field(
        default=None,
        description="Clinical range flag ('normal', 'high', 'critical_high', 'low')",
    )
    document_id: Optional[int] = Field(
        default=None,
        description="Optional foreign key link to a source uploaded ClinicalDocument",
    )


class StructuredLabResponseSchema(BaseModel):
    """Response representation of a structured laboratory measurement."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    document_id: Optional[int] = None
    test_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    flag: Optional[str] = None
    recorded_at: Optional[str] = None
