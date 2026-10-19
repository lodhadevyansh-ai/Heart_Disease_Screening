"""
Machine Learning Inference and Prediction History Routes.

Endpoints:
- GET  /api/v1/predictions/tasks                      : Supported and unsupported task metadata.
- POST /api/v1/assessments/<int:assessment_id>/predictions : Run inference & persist record.
- GET  /api/v1/assessments/<int:assessment_id>/predictions : Retrieve prediction history.
"""

from flask import Blueprint

from backend.schemas.prediction_schema import PredictionRequestSchema
from backend.services.assessment_service import AssessmentService
from backend.services.prediction_service import PredictionService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import jwt_required, verify_patient_access

prediction_bp = Blueprint("prediction_bp", __name__)


@prediction_bp.route("/predictions/tasks", methods=["GET"])
@jwt_required(optional=True)
def get_prediction_tasks():
    """Retrieve catalog of supported ML tasks and explicitly unsupported tasks with rationale."""
    catalog = PredictionService.get_task_catalog()
    return api_response(data=catalog)


@prediction_bp.route("/assessments/<int:assessment_id>/predictions", methods=["POST"])
@jwt_required()
@validate_schema(PredictionRequestSchema)
def run_prediction(assessment_id: int, validated_data: PredictionRequestSchema):
    """
    Execute machine learning prediction for a clinical assessment encounter.
    Maps clinical entities explicitly, rejects unsupported tasks, enforces
    missingness checks, and stores prediction record with target definition.
    """
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    success, pred_record, error_msg, status_code = PredictionService.execute_prediction(
        assessment_id=assessment_id,
        data=validated_data,
    )

    if not success or not pred_record:
        error_name = (
            "Not Found" if status_code == 404
            else "Unprocessable Entity" if status_code == 422
            else "Service Unavailable" if status_code == 503
            else "Bad Request"
        )
        return api_error(status_code, error_name, error_msg or "Prediction failed.")

    return api_response(
        data=pred_record.to_dict(),
        message="Prediction generated and persisted successfully.",
        status_code=200,
    )


@prediction_bp.route("/assessments/<int:assessment_id>/predictions", methods=["GET"])
@jwt_required()
def get_prediction_history(assessment_id: int):
    """Retrieve full chronological prediction history for an assessment encounter."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    history = PredictionService.get_prediction_history(assessment_id)
    return api_response(data=[p.to_dict() for p in history])


@prediction_bp.route("/predictions/<int:prediction_id>", methods=["GET"])
@jwt_required()
def get_prediction_by_id(prediction_id: int):
    """Retrieve an individual model prediction record by ID with ownership verification."""
    from database.models import ModelPrediction
    pred = ModelPrediction.query.filter_by(id=prediction_id).first()
    if not pred:
        return api_error(404, "Not Found", f"Prediction record with ID {prediction_id} not found.")

    auth_check = verify_patient_access(pred.assessment.patient_id)
    if auth_check:
        return auth_check

    return api_response(data=pred.to_dict())


@prediction_bp.route("/assessments/<int:assessment_id>/readiness", methods=["GET"])
@jwt_required()
def get_task_readiness(assessment_id: int):
    """Evaluate feature readiness and missing clinical inputs for supported prediction tasks."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    readiness = PredictionService.check_task_readiness(assessment_id)
    return api_response(data=readiness)

