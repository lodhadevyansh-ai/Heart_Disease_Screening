"""
Machine Learning Prediction Request and Response Schemas.

CRITICAL CLINICAL & ML RULES:
1. Target definitions and model versions are preserved in prediction records.
2. Distinct fields for raw scores vs calibrated probabilities.
3. Unsupported tasks are explicitly rejected with informative clinical rationale.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionRequestSchema(BaseModel):
    """Payload to trigger ML condition-risk evaluation."""
    task_name: Optional[str] = Field(
        default=None,
        description="Clinical task name ('coronary_artery_disease', 'heart_failure_mortality', 'arrhythmia_ecg')",
    )
    task: Optional[str] = Field(
        default=None,
        description="Alias for task_name",
    )
    explain: bool = Field(
        default=True,
        description="Whether to generate local feature explanations (SHAP / perturbation)",
    )
    compute_explanations: Optional[bool] = Field(
        default=None,
        description="Alias for explain",
    )
    # Optional ad-hoc or direct feature overrides.
    # When omitted or empty, features are assembled directly from the assessment's clinical records.
    direct_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Explicit dictionary of model features if running direct inference.",
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_task_and_explain(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if not values.get("task_name") and values.get("task"):
                values["task_name"] = values["task"]
            if values.get("compute_explanations") is not None and "explain" not in values:
                values["explain"] = values["compute_explanations"]
        return values


class ModelPredictionResponseSchema(BaseModel):
    """Complete prediction result representation."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    assessment_id: Optional[int] = None
    task_name: str
    model_name: str
    model_version: str
    target_definition: str
    predicted_class_id: Optional[int] = None
    predicted_class_label: str
    raw_score: Optional[float] = None
    calibrated_probability: Optional[float] = None
    is_probability_calibrated: bool
    decision_threshold: Optional[float] = None
    score_type: str
    input_features_snapshot: Optional[Dict[str, Any]] = None
    explanation_snapshot: Optional[Dict[str, Any]] = None
    clinical_prototype_disclaimer: str
    created_at: Optional[str] = None


class TaskMetadataSchema(BaseModel):
    """Metadata detailing capabilities and clinical limits of an ML model."""
    task_name: str
    supported: bool
    status: str
    description: str
    target_definition: str
    score_type: str
    is_probability_calibrated: bool
    required_features: List[str]
    clinical_limitations: str


class SupportedTasksResponseSchema(BaseModel):
    """Catalog of supported and explicitly unsupported ML tasks."""
    supported_tasks: List[TaskMetadataSchema]
    unsupported_tasks: Dict[str, str]
