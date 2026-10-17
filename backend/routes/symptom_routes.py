"""
Clinical Assessment, Symptom, and Vital Sign Routes.

Endpoints:
- GET  /api/v1/assessments/<int:assessment_id>          : Get complete assessment encounter.
- PUT  /api/v1/assessments/<int:assessment_id>          : Update assessment encounter status/notes.
- GET  /api/v1/assessments/<int:assessment_id>/symptoms : Retrieve patient-reported symptoms.
- POST /api/v1/assessments/<int:assessment_id>/symptoms : Create or update symptoms.
- PUT  /api/v1/assessments/<int:assessment_id>/symptoms : Update symptoms.
- GET  /api/v1/assessments/<int:assessment_id>/vitals   : Retrieve clinically measured vitals.
- POST /api/v1/assessments/<int:assessment_id>/vitals   : Create or update vitals.
- PUT  /api/v1/assessments/<int:assessment_id>/vitals   : Update vitals.
"""

from flask import Blueprint, request

from backend.schemas.symptom_schema import (
    AssessmentUpdateSchema,
    PatientSymptomSchema,
    VitalSignSchema,
)
from backend.services.assessment_service import AssessmentService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import jwt_required, verify_patient_access

symptom_bp = Blueprint("symptom_bp", __name__, url_prefix="/assessments")


@symptom_bp.route("/<int:assessment_id>", methods=["GET"])
@jwt_required()
def get_assessment(assessment_id: int):
    """Retrieve complete assessment encounter with symptoms and vitals."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    data = assessment.to_dict()
    data["clinical_notes"] = assessment.clinical_notes
    data["symptoms"] = assessment.symptoms.to_dict() if assessment.symptoms else None
    data["vitals"] = assessment.vitals.to_dict() if assessment.vitals else None
    data["documents_count"] = len(assessment.documents)
    data["lab_measurements_count"] = len(assessment.lab_measurements)
    data["predictions_count"] = len(assessment.predictions)

    return api_response(data=data)


@symptom_bp.route("/<int:assessment_id>", methods=["PUT"])
@jwt_required()
@validate_schema(AssessmentUpdateSchema)
def update_assessment(assessment_id: int, validated_data: AssessmentUpdateSchema):
    """Update assessment status, visit reason, or notes."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    updated = AssessmentService.update_assessment(assessment_id, validated_data)
    return api_response(
        data=updated.to_dict(),
        message="Assessment updated successfully.",
    )


@symptom_bp.route("/<int:assessment_id>/symptoms", methods=["GET"])
@jwt_required()
def get_symptoms(assessment_id: int):
    """Retrieve patient-reported symptoms."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    symptoms = AssessmentService.get_or_create_symptoms(assessment_id)
    return api_response(data=symptoms.to_dict())


@symptom_bp.route("/<int:assessment_id>/symptoms", methods=["POST", "PUT"])
@jwt_required()
@validate_schema(PatientSymptomSchema)
def save_symptoms(assessment_id: int, validated_data: PatientSymptomSchema):
    """Save or update patient-reported symptoms and run pattern classification."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    symptoms = AssessmentService.save_symptoms(assessment_id, validated_data)
    return api_response(
        data=symptoms.to_dict(),
        message="Symptoms recorded and classified successfully.",
    )


@symptom_bp.route("/<int:assessment_id>/vitals", methods=["GET"])
@jwt_required()
def get_vitals(assessment_id: int):
    """Retrieve clinically measured vital signs. Missing metrics are returned as null."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    vitals = AssessmentService.get_or_create_vitals(assessment_id)
    return api_response(data=vitals.to_dict())


@symptom_bp.route("/<int:assessment_id>/vitals", methods=["POST", "PUT"])
@jwt_required()
@validate_schema(VitalSignSchema)
def save_vitals(assessment_id: int, validated_data: VitalSignSchema):
    """
    Save or update objective vital signs.
    Validates physiological plausibility and maintains nullability for unmeasured values.
    """
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    vitals = AssessmentService.save_vitals(assessment_id, validated_data)
    return api_response(
        data=vitals.to_dict(),
        message="Vitals saved successfully.",
    )
