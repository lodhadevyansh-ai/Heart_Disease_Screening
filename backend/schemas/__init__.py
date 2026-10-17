"""
Centralized Pydantic Schemas for Request and Response Serialization.
"""

from backend.schemas.auth_schemas import (
    LoginRequestSchema,
    TokenResponseSchema,
    UserProfileSchema,
)
from backend.schemas.common_schema import (
    PaginatedResponse,
    PaginationParams,
)
from backend.schemas.patient_schema import (
    PatientCreateSchema,
    PatientResponseSchema,
    PatientUpdateSchema,
)
from backend.schemas.prediction_schema import (
    ModelPredictionResponseSchema,
    PredictionRequestSchema,
    SupportedTasksResponseSchema,
    TaskMetadataSchema,
)
from backend.schemas.recommendation_schema import (
    RecommendationRequestSchema,
    RecommendationResponseSchema,
)
from backend.schemas.report_schema import (
    DocumentUploadResponseSchema,
    StructuredLabCreateSchema,
    StructuredLabResponseSchema,
)
from backend.schemas.symptom_schema import (
    AssessmentCreateSchema,
    AssessmentResponseSchema,
    AssessmentUpdateSchema,
    PatientSymptomSchema,
    VitalSignSchema,
)

__all__ = [
    "LoginRequestSchema",
    "TokenResponseSchema",
    "UserProfileSchema",
    "PaginationParams",
    "PaginatedResponse",
    "PatientCreateSchema",
    "PatientUpdateSchema",
    "PatientResponseSchema",
    "AssessmentCreateSchema",
    "AssessmentUpdateSchema",
    "AssessmentResponseSchema",
    "PatientSymptomSchema",
    "VitalSignSchema",
    "DocumentUploadResponseSchema",
    "StructuredLabCreateSchema",
    "StructuredLabResponseSchema",
    "PredictionRequestSchema",
    "ModelPredictionResponseSchema",
    "TaskMetadataSchema",
    "SupportedTasksResponseSchema",
    "RecommendationRequestSchema",
    "RecommendationResponseSchema",
]
