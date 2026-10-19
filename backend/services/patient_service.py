"""
Patient Profile Management Service.

Enforces HIPAA de-identification standards:
- Generates unique de-identified patient identifiers (e.g. PT-XXXXXXXX).
- Converts external medical record numbers to one-way SHA-256 hashes.
- Supports pagination, searching, and assessment encounters.
"""

import hashlib
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import or_

from backend.extensions import db
from backend.schemas.patient_schema import PatientCreateSchema, PatientUpdateSchema
from database.models import Assessment, Patient


class PatientService:
    """Service managing patient profiles and encounters."""

    @staticmethod
    def generate_patient_code() -> str:
        """Generate a collision-resistant de-identified patient code."""
        while True:
            candidate = f"PT-{uuid.uuid4().hex[:8].upper()}"
            if not Patient.query.filter_by(patient_code=candidate).first():
                return candidate

    @staticmethod
    def hash_mrn(mrn: Optional[str]) -> Optional[str]:
        """Convert external MRN into a one-way cryptographic SHA-256 hash."""
        if not mrn or not mrn.strip():
            return None
        return hashlib.sha256(mrn.strip().encode("utf-8")).hexdigest()

    @classmethod
    def create_patient(cls, data: PatientCreateSchema, user_id: Optional[int] = None) -> Patient:
        """Create a new de-identified patient profile owned by user_id."""
        code = cls.generate_patient_code()
        mrn_hash = cls.hash_mrn(data.medical_record_number)

        patient = Patient(
            user_id=user_id,
            patient_code=code,
            age=data.age,
            sex=data.sex,
            medical_record_number_hash=mrn_hash,
            notes=data.notes,
            is_active=True,
        )
        try:
            db.session.add(patient)
            db.session.commit()
            return patient
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_patient_by_id(patient_id: int) -> Optional[Patient]:
        """Fetch patient by primary key ID."""
        return Patient.query.filter_by(id=patient_id).first()

    @staticmethod
    def get_patient_by_code(patient_code: str) -> Optional[Patient]:
        """Fetch patient by de-identified patient code."""
        return Patient.query.filter_by(patient_code=patient_code).first()

    @classmethod
    def update_patient(cls, patient_id: int, data: PatientUpdateSchema) -> Optional[Patient]:
        """Update an existing patient's demographic details."""
        patient = cls.get_patient_by_id(patient_id)
        if not patient:
            return None

        if data.age is not None:
            patient.age = data.age
        if data.sex is not None:
            patient.sex = data.sex
        if data.notes is not None:
            patient.notes = data.notes
        if data.is_active is not None:
            patient.is_active = data.is_active

        db.session.commit()
        return patient

    @staticmethod
    def list_patients(
        user_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        sex: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Patient], int]:
        """
        List patient profiles with filtering, pagination, and user ownership scoping.

        Returns
        -------
        items : list of Patient
        total : int
        """
        query = Patient.query

        if user_id is not None:
            query = query.filter(Patient.user_id == user_id)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Patient.patient_code.ilike(search_term),
                    Patient.notes.ilike(search_term),
                )
            )

        if sex:
            query = query.filter(Patient.sex.ilike(sex.strip()))

        if is_active is not None:
            query = query.filter(Patient.is_active == is_active)

        total = query.count()
        items = (
            query.order_by(Patient.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    @staticmethod
    def get_patient_assessments(patient_id: int) -> List[Assessment]:
        """List all clinical assessment encounters for a patient."""
        return (
            Assessment.query.filter_by(patient_id=patient_id)
            .order_by(Assessment.assessment_date.desc())
            .all()
        )

    @staticmethod
    def create_assessment_for_patient(
        patient_id: int,
        reason_for_visit: Optional[str] = None,
        clinical_notes: Optional[str] = None,
    ) -> Optional[Assessment]:
        """Initiate a new clinical assessment encounter for a patient."""
        patient = Patient.query.filter_by(id=patient_id).first()
        if not patient:
            return None

        assessment = Assessment(
            patient_id=patient_id,
            reason_for_visit=reason_for_visit,
            clinical_notes=clinical_notes,
            status="in_progress",
        )
        db.session.add(assessment)
        db.session.commit()
        return assessment
