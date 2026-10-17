"""
Patient Profile and Assessment Encounter Routes.

Endpoints:
- GET  /api/v1/patients                        : List patient profiles (paginated, searchable).
- POST /api/v1/patients                        : Create new de-identified patient record.
- GET  /api/v1/patients/<int:patient_id>       : Get patient details.
- PUT  /api/v1/patients/<int:patient_id>       : Update patient demographics.
- GET  /api/v1/patients/<int:patient_id>/assessments : List assessment encounters.
- POST /api/v1/patients/<int:patient_id>/assessments : Initiate new assessment encounter.
"""

from typing import Optional
from flask import Blueprint, request

from backend.schemas.patient_schema import PatientCreateSchema, PatientUpdateSchema
from backend.services.patient_service import PatientService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import (
    get_current_user,
    jwt_required,
    roles_required,
    verify_patient_access,
)

patient_bp = Blueprint("patient_bp", __name__, url_prefix="/patients")


@patient_bp.route("", methods=["GET"])
@jwt_required()
def list_patients():
    """List patient records with pagination and search."""
    user = get_current_user()
    role = user.get("role") if user else None

    # If role is patient, restrict list to their own profile only
    if role == "patient":
        patient_id = user.get("patient_id")
        if not patient_id:
            return api_response(data={"items": [], "total": 0, "page": 1, "per_page": 20, "total_pages": 0})
        patient = PatientService.get_patient_by_id(patient_id)
        items = [patient.to_dict()] if patient else []
        return api_response(
            data={
                "items": items,
                "total": len(items),
                "page": 1,
                "per_page": 20,
                "total_pages": 1 if items else 0,
            }
        )

    # Clinicians and Admins can query all patients
    try:
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 20)), 100)
    except ValueError:
        return api_error(400, "Bad Request", "Pagination query parameters must be integers.")

    search = request.args.get("search")
    sex = request.args.get("sex")
    is_active_raw = request.args.get("is_active")
    is_active = (
        is_active_raw.lower() in ("true", "1")
        if is_active_raw is not None
        else None
    )

    items, total = PatientService.list_patients(
        page=page,
        per_page=per_page,
        search=search,
        sex=sex,
        is_active=is_active,
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

    return api_response(
        data={
            "items": [p.to_dict() for p in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    )


@patient_bp.route("", methods=["POST"])
@jwt_required()
@roles_required("clinician", "admin")
@validate_schema(PatientCreateSchema)
def create_patient(validated_data: PatientCreateSchema):
    """Create a new de-identified patient record."""
    try:
        patient = PatientService.create_patient(validated_data)
        return api_response(
            data=patient.to_dict(),
            message="Patient profile created successfully.",
            status_code=201,
        )
    except Exception as e:
        return api_error(500, "Internal Server Error", f"Failed to persist patient record: {str(e)}")


@patient_bp.route("/<int:patient_id>", methods=["GET"])
@jwt_required()
def get_patient(patient_id: int):
    """Retrieve detailed patient profile."""
    auth_check = verify_patient_access(patient_id)
    if auth_check:
        return auth_check

    patient = PatientService.get_patient_by_id(patient_id)
    if not patient:
        return api_error(404, "Not Found", f"Patient with ID {patient_id} not found.")

    res = patient.to_dict()
    res["notes"] = patient.notes
    return api_response(data=res)


@patient_bp.route("/<int:patient_id>", methods=["PUT"])
@jwt_required()
@roles_required("clinician", "admin")
@validate_schema(PatientUpdateSchema)
def update_patient(patient_id: int, validated_data: PatientUpdateSchema):
    """Update patient demographics or notes."""
    patient = PatientService.update_patient(patient_id, validated_data)
    if not patient:
        return api_error(404, "Not Found", f"Patient with ID {patient_id} not found.")

    res = patient.to_dict()
    res["notes"] = patient.notes
    return api_response(data=res, message="Patient updated successfully.")


@patient_bp.route("/<int:patient_id>/assessments", methods=["GET"])
@jwt_required()
def list_patient_assessments(patient_id: int):
    """List clinical assessment encounters for a patient."""
    auth_check = verify_patient_access(patient_id)
    if auth_check:
        return auth_check

    patient = PatientService.get_patient_by_id(patient_id)
    if not patient:
        return api_error(404, "Not Found", f"Patient with ID {patient_id} not found.")

    assessments = PatientService.get_patient_assessments(patient_id)
    return api_response(data=[a.to_dict() for a in assessments])


@patient_bp.route("/<int:patient_id>/assessments", methods=["POST"])
@jwt_required()
@roles_required("clinician", "admin")
def create_patient_assessment(patient_id: int):
    """Initiate a new clinical assessment encounter."""
    patient = PatientService.get_patient_by_id(patient_id)
    if not patient:
        return api_error(404, "Not Found", f"Patient with ID {patient_id} not found.")

    data = request.get_json(silent=True) or {}
    reason = data.get("reason_for_visit")
    notes = data.get("clinical_notes")

    assessment = PatientService.create_assessment_for_patient(
        patient_id=patient_id,
        reason_for_visit=reason,
        clinical_notes=notes,
    )
    if not assessment:
        return api_error(500, "Internal Server Error", "Could not create assessment.")

    return api_response(
        data=assessment.to_dict(),
        message="Assessment encounter initiated successfully.",
        status_code=201,
    )
