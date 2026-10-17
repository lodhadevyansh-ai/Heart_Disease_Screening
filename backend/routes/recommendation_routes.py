"""
Clinical Safety and Recommendation Routes.

Endpoints:
- POST /api/v1/recommendations/evaluate                : Ad-hoc clinical rule evaluation.
- GET  /api/v1/assessments/<int:assessment_id>/recommendations : Rule evaluation for encounter.
"""

from flask import Blueprint

from backend.schemas.recommendation_schema import RecommendationRequestSchema
from backend.services.assessment_service import AssessmentService
from backend.services.recommendation_service import RecommendationService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import jwt_required, verify_patient_access

recommendation_bp = Blueprint("recommendation_bp", __name__)


@recommendation_bp.route("/recommendations/evaluate", methods=["POST"])
@jwt_required(optional=True)
@validate_schema(RecommendationRequestSchema)
def evaluate_recommendations_ad_hoc(validated_data: RecommendationRequestSchema):
    """
    Evaluate clinical safety rules and secondary diagnostic test recommendations
    against an ad-hoc clinical payload.
    """
    result = RecommendationService.evaluate_ad_hoc(
        patient_symptoms=validated_data.patient_symptoms,
        measured_vitals=validated_data.measured_vitals,
        clinical_history=validated_data.clinical_history,
    )
    return api_response(data=result)


@recommendation_bp.route("/assessments/<int:assessment_id>/recommendations", methods=["GET"])
@jwt_required()
def evaluate_assessment_recommendations(assessment_id: int):
    """
    Execute clinical safety rules on an existing assessment encounter.
    Automatically escalates emergency status if red-flag rules trigger.
    """
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    result = RecommendationService.evaluate_assessment(assessment_id)
    if not result:
        return api_error(500, "Internal Server Error", "Could not complete rule evaluation.")

    return api_response(data=result)
