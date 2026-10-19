"""
Clinical Assessment, Symptom, and Vital Sign Request/Response Schemas.

CRITICAL CLINICAL RULES:
1. Every vital sign is strictly nullable. Missing vitals must NEVER be conflated with 0.0.
2. Physiological plausibility ranges are enforced.
3. Symptoms distinguish unassessed from confirmed absences.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssessmentCreateSchema(BaseModel):
    """Payload to initiate a clinical assessment encounter."""
    patient_id: int = Field(..., description="Target patient record ID")
    reason_for_visit: Optional[str] = Field(default=None, max_length=255)
    clinical_notes: Optional[str] = Field(default=None, max_length=5000)


class AssessmentUpdateSchema(BaseModel):
    """Payload to update an assessment's clinical encounter status and notes."""
    status: Optional[str] = Field(
        default=None,
        description="Encounter status ('in_progress', 'completed', 'flagged_emergency')",
    )
    reason_for_visit: Optional[str] = Field(default=None, max_length=255)
    clinical_notes: Optional[str] = Field(default=None, max_length=5000)
    emergency_escalation_level: Optional[str] = Field(
        default=None,
        description="Emergency level ('EMERGENCY_IMMEDIATE_911', 'URGENT_SAME_DAY', 'NONE')",
    )


class PatientSymptomSchema(BaseModel):
    """
    Patient-reported cardiovascular symptom intake.
    All fields are nullable to distinguish unassessed from denied symptoms.
    """
    chest_pain: Optional[bool] = None
    chest_pain_quality: Optional[str] = Field(default=None, max_length=50)
    chest_pain_radiation: Optional[str] = Field(default=None, max_length=100)
    substernal_location: Optional[bool] = None
    exertional_provocation: Optional[bool] = None
    relieved_by_rest: Optional[bool] = None
    rest_or_nitroglycerin_relief: Optional[bool] = None

    dyspnea: Optional[bool] = None
    shortness_of_breath: Optional[bool] = None
    dyspnea_at_rest: Optional[bool] = None
    orthopnea: Optional[bool] = None
    paroxysmal_nocturnal_dyspnea: Optional[bool] = None

    palpitations: Optional[bool] = None
    syncope: Optional[bool] = None
    syncope_during_exertion: Optional[bool] = None
    diaphoresis: Optional[bool] = None
    bilateral_leg_edema: Optional[bool] = None
    claudication: Optional[bool] = None

    angina_classification: Optional[str] = Field(
        default=None,
        description="'typical_angina', 'atypical_angina', 'non_anginal', or 'none'",
    )
    congestive_score: Optional[int] = Field(default=None, ge=0, le=10)
    symptom_notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="before")
    @classmethod
    def reconcile_symptom_aliases(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get("relieved_by_rest") is None and values.get("rest_or_nitroglycerin_relief") is not None:
                values["relieved_by_rest"] = values["rest_or_nitroglycerin_relief"]
            if values.get("dyspnea") is None and values.get("shortness_of_breath") is not None:
                values["dyspnea"] = values["shortness_of_breath"]
        return values


class VitalSignSchema(BaseModel):
    """
    Objective measured physiological metrics.
    
    CRITICAL RULE:
    Strictly nullable; missing measurements must remain None (SQL NULL).
    """
    systolic_bp: Optional[float] = Field(
        default=None,
        ge=40.0,
        le=300.0,
        description="Resting Systolic Blood Pressure (mm Hg) [40 - 300]",
    )
    diastolic_bp: Optional[float] = Field(
        default=None,
        ge=20.0,
        le=200.0,
        description="Resting Diastolic Blood Pressure (mm Hg) [20 - 200]",
    )
    heart_rate: Optional[float] = Field(
        default=None,
        ge=20.0,
        le=300.0,
        description="Resting Heart Rate (bpm) [20 - 300]",
    )
    respiratory_rate: Optional[float] = Field(
        default=None,
        ge=4.0,
        le=70.0,
        description="Respiratory Rate (breaths/min) [4 - 70]",
    )
    spo2: Optional[float] = Field(
        default=None,
        ge=50.0,
        le=100.0,
        description="Pulse Oximetry Oxygen Saturation (%) [50 - 100]",
    )
    temperature_celsius: Optional[float] = Field(
        default=None,
        ge=30.0,
        le=45.0,
        description="Body Temperature in Celsius [30 - 45]",
    )
    height_cm: Optional[float] = Field(
        default=None,
        ge=40.0,
        le=250.0,
        description="Height in centimeters [40 - 250]",
    )
    weight_kg: Optional[float] = Field(
        default=None,
        ge=2.0,
        le=350.0,
        description="Body Weight in kilograms [2 - 350]",
    )
    bmi: Optional[float] = Field(
        default=None,
        ge=10.0,
        le=90.0,
        description="Body Mass Index (kg/m²)",
    )

    @field_validator("diastolic_bp")
    @classmethod
    def validate_bp_relationship(cls, v: Optional[float], info: Any) -> Optional[float]:
        # Validate that diastolic does not exceed systolic if both are supplied
        systolic = info.data.get("systolic_bp")
        if v is not None and systolic is not None and v >= systolic:
            raise ValueError(f"Diastolic BP ({v}) cannot be greater than or equal to Systolic BP ({systolic}).")
        return v


class AssessmentResponseSchema(BaseModel):
    """Detailed response representation of an assessment encounter."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_code: Optional[str] = None
    assessment_date: Optional[str] = None
    status: str
    reason_for_visit: Optional[str] = None
    clinical_notes: Optional[str] = None
    emergency_escalation_level: Optional[str] = None
    created_at: Optional[str] = None
    symptoms: Optional[Dict[str, Any]] = None
    vitals: Optional[Dict[str, Any]] = None
    documents_count: int = 0
    lab_measurements_count: int = 0
    predictions_count: int = 0
