"""
Clinical Safety and Recommendation Request/Response Schemas.

Enforces emergency rule primacy over routine workflows.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequestSchema(BaseModel):
    """Payload to perform an ad-hoc clinical recommendation evaluation."""
    patient_symptoms: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Patient-reported symptoms (chest pain, dyspnea, palpitations, syncope, etc.)",
    )
    measured_vitals: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Physiologically measured metrics (systolic_bp, heart_rate, spo2, etc.)",
    )
    clinical_history: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Demographics and history (age, sex, known CAD, diabetes, hypertension)",
    )


class RecommendationResponseSchema(BaseModel):
    """Structured clinical decision support payload."""
    status: str
    is_emergency: bool
    overall_urgency: str
    emergency_triage: Dict[str, Any]
    symptom_evaluation: Dict[str, Any]
    diagnostic_recommendations: Dict[str, Any]
    clinical_safety_notice: str
    disclaimer: str
