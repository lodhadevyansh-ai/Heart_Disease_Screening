"""
Relational Database Models for Clinical Persistence.

Defines SQLAlchemy entities for:
1. Patient profiles (de-identified identifiers, demographics).
2. Clinical assessments.
3. Patient-reported symptoms.
4. Objective vital sign measurements (strictly distinguishing missing values from zero).
5. Clinical document/uploaded file metadata (strictly separated from structured measurements).
6. Structured laboratory and report values.
7. Model prediction results with full target definitions, model versions, and feature snapshots.

CLINICAL & PRIVACY MANDATES:
- Anonymized patient codes and hashed medical record numbers to prevent plaintext PHI storage.
- Nullable clinical measurements so unmeasured parameters are NEVER conflated with 0.0.
- Uploaded file metadata stored separately from validated, structured clinical values.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from werkzeug.security import check_password_hash, generate_password_hash
from backend.extensions import db


def to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    Format a datetime object into a standardized, timezone-aware ISO 8601 string
    with an explicit 'Z' UTC designator.
    If dt is naive, explicitly localize to UTC (since all timestamps are recorded in UTC).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    iso = dt.isoformat()
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


class BaseModel(db.Model):
    """Abstract base model defining explicit __init__ for static type checkers."""

    __abstract__ = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class User(BaseModel):
    """
    Authenticated user account.

    Stores credentials, role, and metadata for clinicians, patients, and administrators.
    Passwords are exclusively stored as one-way cryptographic hashes.
    """

    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    username = Column(String(60), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), default="patient", nullable=False)  # 'patient', 'clinician', 'admin'
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient_profile = relationship("Patient", foreign_keys=[patient_id])
    patients = relationship("Patient", foreign_keys="[Patient.user_id]", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        """Return safe user profile dictionary (excluding password hash)."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "name": self.full_name,
            "email": self.email,
            "username": self.username or self.email,
            "role": self.role,
            "patient_id": self.patient_id,
            "is_active": self.is_active,
            "created_at": to_iso_utc(self.created_at),
            "updated_at": to_iso_utc(self.updated_at),
        }


class Patient(BaseModel):
    """
    Patient demographic and profile record.
    
    Adheres to HIPAA de-identification by using unique patient codes
    and one-way cryptographic hashes for external medical record numbers.
    """

    __tablename__ = "patients"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    patient_code = Column(String(36), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(String(10), nullable=False)  # 'Male', 'Female'
    medical_record_number_hash = Column(String(64), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="patients")
    assessments = relationship(
        "Assessment",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(Assessment.assessment_date)",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "patient_code": self.patient_code,
            "age": self.age,
            "sex": self.sex,
            "is_active": self.is_active,
            "assessments_count": len(self.assessments) if self.assessments is not None else 0,
            "created_at": to_iso_utc(self.created_at),
            "updated_at": to_iso_utc(self.updated_at),
        }


class Assessment(BaseModel):
    """
    Clinical encounter / evaluation record grouping symptoms, vitals,
    uploaded document metadata, and ML predictions.
    """

    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    status = Column(String(30), default="completed", nullable=False)  # 'in_progress', 'completed', 'flagged_emergency'
    reason_for_visit = Column(String(255), nullable=True)
    clinical_notes = Column(Text, nullable=True)
    emergency_escalation_level = Column(String(50), nullable=True)  # 'EMERGENCY_IMMEDIATE_911', 'NONE'

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient = relationship("Patient", back_populates="assessments")
    symptoms = relationship("PatientSymptom", back_populates="assessment", uselist=False, cascade="all, delete-orphan")
    vitals = relationship("VitalSign", back_populates="assessment", uselist=False, cascade="all, delete-orphan")
    documents = relationship("ClinicalDocument", back_populates="assessment", cascade="all, delete-orphan")
    lab_measurements = relationship("StructuredLabMeasurement", back_populates="assessment", cascade="all, delete-orphan")
    predictions = relationship("ModelPrediction", back_populates="assessment", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_code": self.patient.patient_code if self.patient else None,
            "patient": self.patient.to_dict() if self.patient else None,
            "assessment_date": to_iso_utc(self.assessment_date),
            "status": self.status,
            "reason_for_visit": self.reason_for_visit,
            "emergency_escalation_level": self.emergency_escalation_level,
            "created_at": to_iso_utc(self.created_at),
        }


class PatientSymptom(BaseModel):
    """
    Patient-reported subjective cardiovascular symptoms.
    
    All symptom flags are nullable so that unassessed/unasked symptoms
    are distinguished from confirmed absences.
    """

    __tablename__ = "patient_symptoms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    chest_pain = Column(Boolean, nullable=True)
    chest_pain_quality = Column(String(50), nullable=True)  # 'crushing', 'sharp', 'pressure', 'tightness'
    chest_pain_radiation = Column(String(100), nullable=True)  # 'left arm', 'jaw', 'back'
    substernal_location = Column(Boolean, nullable=True)
    exertional_provocation = Column(Boolean, nullable=True)
    relieved_by_rest = Column(Boolean, nullable=True)

    dyspnea = Column(Boolean, nullable=True)
    dyspnea_at_rest = Column(Boolean, nullable=True)
    orthopnea = Column(Boolean, nullable=True)
    paroxysmal_nocturnal_dyspnea = Column(Boolean, nullable=True)

    palpitations = Column(Boolean, nullable=True)
    syncope = Column(Boolean, nullable=True)
    syncope_during_exertion = Column(Boolean, nullable=True)
    diaphoresis = Column(Boolean, nullable=True)
    bilateral_leg_edema = Column(Boolean, nullable=True)
    claudication = Column(Boolean, nullable=True)

    angina_classification = Column(String(30), nullable=True)  # 'typical_angina', 'atypical_angina', 'non_anginal', 'none'
    congestive_score = Column(Integer, nullable=True)
    symptom_notes = Column(Text, nullable=True)

    reported_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="symptoms")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "chest_pain": self.chest_pain,
            "chest_pain_quality": self.chest_pain_quality,
            "chest_pain_radiation": self.chest_pain_radiation,
            "substernal_location": self.substernal_location,
            "exertional_provocation": self.exertional_provocation,
            "relieved_by_rest": self.relieved_by_rest,
            "dyspnea": self.dyspnea,
            "dyspnea_at_rest": self.dyspnea_at_rest,
            "orthopnea": self.orthopnea,
            "paroxysmal_nocturnal_dyspnea": self.paroxysmal_nocturnal_dyspnea,
            "palpitations": self.palpitations,
            "syncope": self.syncope,
            "diaphoresis": self.diaphoresis,
            "bilateral_leg_edema": self.bilateral_leg_edema,
            "claudication": self.claudication,
            "angina_classification": self.angina_classification,
            "congestive_score": self.congestive_score,
            "reported_at": to_iso_utc(self.reported_at),
        }


class VitalSign(BaseModel):
    """
    Clinically measured physiological metrics.
    
    CRITICAL RULE:
    Every measured vital is strictly nullable with NO default value.
    Missing measurements are stored as NULL, never as 0.0.
    """

    __tablename__ = "vital_signs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    systolic_bp = Column(Float, nullable=True)  # mm Hg
    diastolic_bp = Column(Float, nullable=True)  # mm Hg
    heart_rate = Column(Float, nullable=True)  # bpm
    respiratory_rate = Column(Float, nullable=True)  # breaths/min
    spo2 = Column(Float, nullable=True)  # %
    temperature_celsius = Column(Float, nullable=True)  # °C
    height_cm = Column(Float, nullable=True)  # cm
    weight_kg = Column(Float, nullable=True)  # kg
    bmi = Column(Float, nullable=True)  # kg/m²

    measured_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="vitals")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
            "heart_rate": self.heart_rate,
            "respiratory_rate": self.respiratory_rate,
            "spo2": self.spo2,
            "temperature_celsius": self.temperature_celsius,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "measured_at": to_iso_utc(self.measured_at),
        }


class ClinicalDocument(BaseModel):
    """
    Uploaded file metadata.
    
    CRITICAL RULE:
    File metadata is stored separately from structured clinical values.
    An uploaded PDF or image is an unstructured binary asset and is NOT
    treated as extracted clinical data until verified.
    """

    __tablename__ = "clinical_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(20), nullable=False)  # 'pdf', 'image_png', 'image_jpeg'
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    document_category = Column(String(50), nullable=False)  # 'ecg_report_pdf', 'lab_results', 'clinical_note'
    parsing_status = Column(String(30), default="stored_unparsed", nullable=False)
    is_verified_by_clinician = Column(Boolean, default=False, nullable=False)

    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="documents")
    lab_measurements = relationship("StructuredLabMeasurement", back_populates="source_document")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "document_category": self.document_category,
            "parsing_status": self.parsing_status,
            "is_verified_by_clinician": self.is_verified_by_clinician,
            "uploaded_at": to_iso_utc(self.uploaded_at),
            "created_at": to_iso_utc(self.uploaded_at),
            "extracted_measurements_count": len(self.lab_measurements) if self.lab_measurements is not None else 0,
        }


class StructuredLabMeasurement(BaseModel):
    """
    Structured laboratory and clinical report values.
    
    Can optionally be linked to a source ClinicalDocument if extracted,
    or entered directly during clinical intake.
    """

    __tablename__ = "structured_lab_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("clinical_documents.id", ondelete="SET NULL"), nullable=True, index=True)

    test_name = Column(String(100), nullable=False, index=True)  # e.g. 'cholesterol', 'troponin_i', 'bnp', 'ejection_fraction'
    value_numeric = Column(Float, nullable=True)  # Nullable: distinguishes missing from 0.0
    value_text = Column(String(100), nullable=True)  # e.g. '<0.01', 'normal', 'negative'
    unit = Column(String(30), nullable=True)  # 'mg/dL', 'pg/mL', '%', 'mcg/L'
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    flag = Column(String(20), nullable=True)  # 'normal', 'high', 'critical_high', 'low'

    recorded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="lab_measurements")
    source_document = relationship("ClinicalDocument", back_populates="lab_measurements")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "document_id": self.document_id,
            "test_name": self.test_name,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "unit": self.unit,
            "reference_low": self.reference_low,
            "reference_high": self.reference_high,
            "flag": self.flag,
            "recorded_at": to_iso_utc(self.recorded_at),
        }


class ModelPrediction(BaseModel):
    """
    Persisted Machine Learning prediction result.
    
    CRITICAL RULE:
    Stores the exact target definition, model version, and input feature snapshot
    alongside the prediction score to ensure retrospective clinical auditability.
    """

    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    task_name = Column(String(60), nullable=False, index=True)  # 'coronary_artery_disease', 'heart_failure_mortality', 'arrhythmia_ecg'
    model_name = Column(String(120), nullable=False)
    model_version = Column(String(30), nullable=False)
    target_definition = Column(Text, nullable=False)  # Exact retrospective label meaning

    predicted_class_id = Column(Integer, nullable=True)
    predicted_class_label = Column(String(100), nullable=False)
    raw_score = Column(Float, nullable=True)
    calibrated_probability = Column(Float, nullable=True)
    is_probability_calibrated = Column(Boolean, default=False, nullable=False)
    decision_threshold = Column(Float, nullable=True)
    score_type = Column(String(50), nullable=False)

    input_features_snapshot = Column(JSON, nullable=True)  # Exact input vector fed to pipeline
    explanation_snapshot = Column(JSON, nullable=True)  # SHAP or perturbation attributions
    clinical_prototype_disclaimer = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    assessment = relationship("Assessment", back_populates="predictions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assessment_id": self.assessment_id,
            "task_name": self.task_name,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "target_definition": self.target_definition,
            "predicted_class_id": self.predicted_class_id,
            "predicted_class_label": self.predicted_class_label,
            "raw_score": self.raw_score,
            "calibrated_probability": self.calibrated_probability,
            "is_probability_calibrated": self.is_probability_calibrated,
            "decision_threshold": self.decision_threshold,
            "score_type": self.score_type,
            "input_features_snapshot": self.input_features_snapshot,
            "explanation_snapshot": self.explanation_snapshot,
            "clinical_prototype_disclaimer": self.clinical_prototype_disclaimer,
            "created_at": to_iso_utc(self.created_at),
        }


# Composite Indexes for efficient querying
Index("idx_patient_assessment_date", Assessment.patient_id, Assessment.assessment_date)
Index("idx_lab_assessment_test", StructuredLabMeasurement.assessment_id, StructuredLabMeasurement.test_name)
Index("idx_prediction_assessment_task", ModelPrediction.assessment_id, ModelPrediction.task_name)
