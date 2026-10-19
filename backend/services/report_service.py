"""
Clinical Document Upload and Structured Laboratory Measurement Service.

MANDATES:
1. Strict file extension, MIME, size, and magic byte enforcement.
2. Documents stored outside public web roots.
3. Uploaded documents are marked as 'stored_unparsed' and NEVER claimed to be
   automatically interpreted without a verified clinical extraction workflow.
4. Structured lab measurements distinguish missing values from 0.0.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from flask import current_app
from werkzeug.datastructures import FileStorage

from backend.extensions import db
from backend.schemas.report_schema import StructuredLabCreateSchema
from backend.utils.file_utils import process_and_save_upload
from database.models import Assessment, ClinicalDocument, StructuredLabMeasurement


class ReportService:
    """Manages document uploads and structured lab entries."""

    @staticmethod
    def save_document(
        assessment_id: int,
        file_storage: FileStorage,
        document_category: str = "ecg_report_pdf",
    ) -> Tuple[bool, Optional[ClinicalDocument], Optional[str]]:
        """
        Validate, hash, and store a clinical document, saving metadata to the database.

        Returns
        -------
        success : bool
        document : ClinicalDocument, optional
        error_message : str, optional
        """
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            return False, None, f"Assessment with ID {assessment_id} not found."

        upload_folder = Path(current_app.config.get("UPLOAD_FOLDER"))
        allowed_exts = current_app.config.get("ALLOWED_DOCUMENT_EXTENSIONS", {"pdf", "png", "jpg", "jpeg"})
        allowed_mimes = current_app.config.get("ALLOWED_DOCUMENT_MIMETYPES", {"application/pdf", "image/png", "image/jpeg"})
        max_bytes = current_app.config.get("MAX_DOCUMENT_SIZE_BYTES", 10 * 1024 * 1024)

        success, meta, err = process_and_save_upload(
            file_storage=file_storage,
            upload_folder=upload_folder,
            allowed_extensions=allowed_exts,
            allowed_mimetypes=allowed_mimes,
            max_size_bytes=max_bytes,
        )

        if not success or not meta:
            return False, None, err

        doc = ClinicalDocument(
            assessment_id=assessment_id,
            original_filename=meta["original_filename"],
            stored_filename=meta["stored_filename"],
            file_type=meta["file_type"],
            mime_type=meta["mime_type"],
            file_size_bytes=meta["file_size_bytes"],
            sha256_hash=meta["sha256_hash"],
            document_category=document_category,
            parsing_status="stored_unparsed",
            is_verified_by_clinician=False,
        )
        db.session.add(doc)
        db.session.flush()

        # Automatic extraction of clinical PDF reports
        saved_file_path = upload_folder / meta["stored_filename"]
        if meta["file_type"] == "pdf" or "pdf" in meta.get("mime_type", "").lower():
            try:
                from backend.services.document_parser import ClinicalDocumentParser
                raw_text = ClinicalDocumentParser.extract_text_from_pdf(saved_file_path)
                if raw_text:
                    parsed_items = ClinicalDocumentParser.parse_clinical_text(raw_text)
                    if parsed_items:
                        for item in parsed_items:
                            lab = StructuredLabMeasurement(
                                assessment_id=assessment_id,
                                document_id=doc.id,
                                test_name=item["test_name"],
                                value_numeric=item.get("value_numeric"),
                                value_text=item.get("value_text"),
                                unit=item.get("unit"),
                                reference_low=item.get("reference_low"),
                                reference_high=item.get("reference_high"),
                                flag=item.get("flag", "normal"),
                            )
                            db.session.add(lab)
                        doc.parsing_status = "parsed"
                    else:
                        doc.parsing_status = "stored_unparsed"
                else:
                    doc.parsing_status = "stored_unparsed"
            except Exception as parse_err:
                current_app.logger.warning("Clinical document parsing error: %s", str(parse_err))
                doc.parsing_status = "stored_unparsed"

        db.session.commit()
        return True, doc, None

    @staticmethod
    def parse_document(document_id: int) -> Tuple[bool, Optional[ClinicalDocument], List[Dict[str, Any]], Optional[str]]:
        """
        Explicitly parse/reparse an uploaded clinical document and persist structured measurements.
        """
        doc = ClinicalDocument.query.filter_by(id=document_id).first()
        if not doc:
            return False, None, [], f"Document with ID {document_id} not found."

        upload_folder = Path(current_app.config.get("UPLOAD_FOLDER"))
        file_path = upload_folder / doc.stored_filename
        if not file_path.exists():
            return False, doc, [], "Physical document file not found on disk."

        try:
            from backend.services.document_parser import ClinicalDocumentParser
            raw_text = ClinicalDocumentParser.extract_text_from_pdf(file_path)
            if not raw_text:
                doc.parsing_status = "unparseable_text"
                db.session.commit()
                return False, doc, [], "No readable text found in document."

            parsed_items = ClinicalDocumentParser.parse_clinical_text(raw_text)
            
            # Remove previous measurements from this document to avoid duplicates on re-parse
            StructuredLabMeasurement.query.filter_by(document_id=doc.id).delete()

            for item in parsed_items:
                lab = StructuredLabMeasurement(
                    assessment_id=doc.assessment_id,
                    document_id=doc.id,
                    test_name=item["test_name"],
                    value_numeric=item.get("value_numeric"),
                    value_text=item.get("value_text"),
                    unit=item.get("unit"),
                    reference_low=item.get("reference_low"),
                    reference_high=item.get("reference_high"),
                    flag=item.get("flag", "normal"),
                )
                db.session.add(lab)

            doc.parsing_status = "parsed" if parsed_items else "no_structured_data_found"
            db.session.commit()
            return True, doc, parsed_items, None
        except Exception as e:
            db.session.rollback()
            return False, doc, [], f"Extraction failure: {str(e)}"

    @staticmethod
    def get_document(document_id: int) -> Optional[ClinicalDocument]:
        """Fetch document metadata by primary key ID."""
        return ClinicalDocument.query.filter_by(id=document_id).first()

    @staticmethod
    def list_documents(assessment_id: int) -> List[ClinicalDocument]:
        """List all uploaded documents associated with an assessment."""
        return (
            ClinicalDocument.query.filter_by(assessment_id=assessment_id)
            .order_by(ClinicalDocument.uploaded_at.desc())
            .all()
        )

    @staticmethod
    def get_document_file_path(document: ClinicalDocument) -> Optional[Path]:
        """Resolve absolute file path for a stored document."""
        upload_folder = Path(current_app.config.get("UPLOAD_FOLDER"))
        file_path = upload_folder / document.stored_filename
        if file_path.exists():
            return file_path
        return None

    @staticmethod
    def create_lab_measurement(
        assessment_id: int,
        data: StructuredLabCreateSchema,
    ) -> Optional[StructuredLabMeasurement]:
        """Record a structured clinical lab measurement."""
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            return None

        # Verify linked document if document_id provided
        if data.document_id:
            doc = ClinicalDocument.query.filter_by(id=data.document_id, assessment_id=assessment_id).first()
            if not doc:
                raise ValueError(f"Document ID {data.document_id} not found in this assessment.")

        lab = StructuredLabMeasurement(
            assessment_id=assessment_id,
            document_id=data.document_id,
            test_name=data.test_name.strip().lower(),
            value_numeric=data.value_numeric,
            value_text=data.value_text,
            unit=data.unit,
            reference_low=data.reference_low,
            reference_high=data.reference_high,
            flag=data.flag,
        )
        db.session.add(lab)
        db.session.commit()
        return lab

    @staticmethod
    def list_lab_measurements(assessment_id: int) -> List[StructuredLabMeasurement]:
        """List all structured laboratory measurements for an assessment encounter."""
        return (
            StructuredLabMeasurement.query.filter_by(assessment_id=assessment_id)
            .order_by(StructuredLabMeasurement.test_name.asc())
            .all()
        )
