"""
Clinical Document Upload and Structured Lab Entry Routes.

MANDATES:
1. Strict file extension, MIME, size, and magic byte validation.
2. Binary assets stored securely outside public web directories.
3. Raw uploaded documents are recorded with status 'stored_unparsed' and
   NEVER claimed to be automatically interpreted.
4. Structured laboratory measurements preserve numeric precision and nullability.
"""

from flask import Blueprint, request, send_file

from backend.schemas.report_schema import StructuredLabCreateSchema
from backend.services.assessment_service import AssessmentService
from backend.services.report_service import ReportService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import jwt_required, verify_patient_access

report_bp = Blueprint("report_bp", __name__)


@report_bp.route("/assessments/<int:assessment_id>/documents", methods=["POST"])
@jwt_required()
def upload_document(assessment_id: int):
    """
    Upload a clinical report document (PDF, PNG, JPG, JPEG).
    Validates file integrity, enforces size limits, stores privately,
    and returns document metadata without claiming unverified automated interpretation.
    """
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    if "file" not in request.files:
        return api_error(400, "Bad Request", "Missing 'file' field in multipart form upload.")

    file_obj = request.files["file"]
    document_category = request.form.get("document_category", "ecg_report_pdf")

    success, doc, error_msg = ReportService.save_document(
        assessment_id=assessment_id,
        file_storage=file_obj,
        document_category=document_category,
    )

    if not success or not doc:
        return api_error(400, "Bad Request", error_msg or "File upload failed.")

    data = doc.to_dict()
    data["extraction_notice"] = (
        "Document securely stored outside public directory. "
        "No automated diagnostic interpretation performed on unverified raw files."
    )

    return api_response(
        data=data,
        message="Document uploaded and stored successfully.",
        status_code=201,
    )


@report_bp.route("/assessments/<int:assessment_id>/documents", methods=["GET"])
@jwt_required()
def list_documents(assessment_id: int):
    """List all uploaded documents associated with an assessment encounter."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    docs = ReportService.list_documents(assessment_id)
    return api_response(data=[d.to_dict() for d in docs])


@report_bp.route("/documents/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document_metadata(document_id: int):
    """Retrieve metadata for a specific uploaded document."""
    doc = ReportService.get_document(document_id)
    if not doc:
        return api_error(404, "Not Found", f"Document with ID {document_id} not found.")

    auth_check = verify_patient_access(doc.assessment.patient_id)
    if auth_check:
        return auth_check

    return api_response(data=doc.to_dict())


@report_bp.route("/documents/<int:document_id>/download", methods=["GET"])
@jwt_required()
def download_document(document_id: int):
    """Securely stream/download an uploaded clinical document from private storage."""
    doc = ReportService.get_document(document_id)
    if not doc:
        return api_error(404, "Not Found", f"Document with ID {document_id} not found.")

    auth_check = verify_patient_access(doc.assessment.patient_id)
    if auth_check:
        return auth_check

    file_path = ReportService.get_document_file_path(doc)
    if not file_path or not file_path.exists():
        return api_error(404, "Not Found", "Physical file not found in private document repository.")

    return send_file(
        file_path,
        mimetype=doc.mime_type,
        as_attachment=True,
        download_name=doc.original_filename,
    )


@report_bp.route("/assessments/<int:assessment_id>/labs", methods=["POST"])
@jwt_required()
@validate_schema(StructuredLabCreateSchema)
def create_lab_measurement(assessment_id: int, validated_data: StructuredLabCreateSchema):
    """Add a structured clinical laboratory measurement."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    try:
        lab = ReportService.create_lab_measurement(assessment_id, validated_data)
        if not lab:
            return api_error(500, "Internal Server Error", "Could not record lab measurement.")
    except ValueError as e:
        return api_error(400, "Bad Request", str(e))

    return api_response(
        data=lab.to_dict(),
        message="Structured laboratory measurement recorded successfully.",
        status_code=201,
    )


@report_bp.route("/assessments/<int:assessment_id>/labs", methods=["GET"])
@jwt_required()
def list_lab_measurements(assessment_id: int):
    """List all structured laboratory measurements for an assessment encounter."""
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return api_error(404, "Not Found", f"Assessment with ID {assessment_id} not found.")

    auth_check = verify_patient_access(assessment.patient_id)
    if auth_check:
        return auth_check

    labs = ReportService.list_lab_measurements(assessment_id)
    return api_response(data=[lab.to_dict() for lab in labs])
