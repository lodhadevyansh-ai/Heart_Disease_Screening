"""
Tests for Relational Database Persistence and Clinical Models (Phase 10).

Validates:
1. Patient creation, de-identification, and hash-based privacy.
2. Assessment relationships and cascading deletion.
3. Strict distinction between missing measurements (NULL) and genuine zero values (0.0).
4. Separation of uploaded file metadata from structured clinical values.
5. Storage of target definitions, model versions, and feature snapshots with predictions.
6. Unique constraints and foreign key integrity.
7. Synthetic demo data seeder execution.
"""

import hashlib
import pytest
from sqlalchemy.exc import IntegrityError

from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.db import ping_database, transaction_scope
from database.models import (
    Patient,
    Assessment,
    PatientSymptom,
    VitalSign,
    ClinicalDocument,
    StructuredLabMeasurement,
    ModelPrediction,
)
from database.seed_demo_data import seed_synthetic_data


@pytest.fixture
def app():
    """Create test application with in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def session(app):
    """Provide clean database session."""
    with app.app_context():
        yield db.session


class TestDatabaseModelsAndIntegrity:
    """Test suite for clinical models, constraints, and relationships."""

    def test_database_connection_ping(self, app):
        with app.app_context():
            assert ping_database() is True

    def test_patient_creation_and_privacy_hashing(self, session):
        mrn_plain = "HOSPITAL-MRN-98421"
        hashed_mrn = hashlib.sha256(mrn_plain.encode("utf-8")).hexdigest()

        patient = Patient(
            patient_code="TEST-PT-001",
            age=55,
            sex="Male",
            medical_record_number_hash=hashed_mrn,
            notes="Test patient for integrity checks.",
            is_active=True,
        )
        session.add(patient)
        session.commit()

        queried = Patient.query.filter_by(patient_code="TEST-PT-001").first()
        assert queried is not None
        assert queried.age == 55
        assert queried.sex == "Male"
        assert queried.medical_record_number_hash == hashed_mrn
        # Plaintext MRN is never stored
        assert mrn_plain not in str(queried.to_dict())

    def test_unique_patient_code_constraint(self, session):
        p1 = Patient(patient_code="DUPLICATE-CODE", age=40, sex="Female")
        p2 = Patient(patient_code="DUPLICATE-CODE", age=42, sex="Male")
        session.add(p1)
        session.commit()

        session.add(p2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_assessment_relationships_and_cascades(self, session):
        patient = Patient(patient_code="TEST-CASCADE-01", age=60, sex="Male")
        session.add(patient)
        session.flush()

        assessment = Assessment(
            patient_id=patient.id,
            status="completed",
            reason_for_visit="Cardiac assessment",
        )
        session.add(assessment)
        session.flush()

        symptoms = PatientSymptom(
            assessment_id=assessment.id,
            chest_pain=True,
            chest_pain_quality="pressure",
            angina_classification="typical_angina",
        )
        vitals = VitalSign(
            assessment_id=assessment.id,
            systolic_bp=135.0,
            diastolic_bp=85.0,
            heart_rate=72.0,
        )
        session.add_all([symptoms, vitals])
        session.commit()

        # Check navigation
        assert assessment.symptoms.chest_pain is True
        assert assessment.vitals.systolic_bp == 135.0
        assert len(patient.assessments) == 1

        # Deleting patient cascades to assessment, symptoms, and vitals
        session.delete(patient)
        session.commit()

        assert Patient.query.filter_by(patient_code="TEST-CASCADE-01").first() is None
        assert Assessment.query.filter_by(id=assessment.id).first() is None
        assert PatientSymptom.query.filter_by(assessment_id=assessment.id).first() is None
        assert VitalSign.query.filter_by(assessment_id=assessment.id).first() is None

    def test_vitals_distinguishes_missing_from_zero(self, session):
        patient = Patient(patient_code="TEST-VITALS-NULL", age=50, sex="Female")
        session.add(patient)
        session.flush()

        assessment = Assessment(patient_id=patient.id)
        session.add(assessment)
        session.flush()

        # Systolic BP measured, but respiratory_rate and temperature unmeasured (NULL)
        vitals = VitalSign(
            assessment_id=assessment.id,
            systolic_bp=128.0,
            diastolic_bp=82.0,
            respiratory_rate=None,  # Not measured
            temperature_celsius=None,  # Not measured
        )
        session.add(vitals)
        session.commit()

        queried_vitals = VitalSign.query.filter_by(assessment_id=assessment.id).first()
        assert queried_vitals.systolic_bp == 128.0
        # Crucial check: missing measurement MUST be None, NEVER defaulted to 0.0
        assert queried_vitals.respiratory_rate is None
        assert queried_vitals.respiratory_rate != 0.0
        assert queried_vitals.temperature_celsius is None

    def test_uploaded_document_metadata_separated_from_measurements(self, session):
        patient = Patient(patient_code="TEST-DOC-SEP", age=55, sex="Male")
        session.add(patient)
        session.flush()

        assessment = Assessment(patient_id=patient.id)
        session.add(assessment)
        session.flush()

        # Upload document metadata (PDF)
        doc = ClinicalDocument(
            assessment_id=assessment.id,
            original_filename="hospital_ecg_trace.pdf",
            stored_filename="secure_storage_ecg_001.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size_bytes=248100,
            sha256_hash=hashlib.sha256(b"SAMPLE_PDF_BYTES").hexdigest(),
            document_category="ecg_report_pdf",
            parsing_status="stored_unparsed",
            is_verified_by_clinician=False,
        )
        session.add(doc)
        session.commit()

        # Document is an asset; no structured lab measurements exist automatically
        assert len(assessment.documents) == 1
        assert len(assessment.lab_measurements) == 0
        assert doc.is_verified_by_clinician is False

        # Add an explicitly verified structured lab measurement linked to doc
        lab = StructuredLabMeasurement(
            assessment_id=assessment.id,
            document_id=doc.id,
            test_name="troponin_i",
            value_numeric=0.02,
            unit="ng/mL",
            flag="normal",
        )
        session.add(lab)
        session.commit()

        assert len(assessment.lab_measurements) == 1
        assert assessment.lab_measurements[0].test_name == "troponin_i"
        assert assessment.lab_measurements[0].document_id == doc.id

    def test_model_prediction_persistence_and_target_definition(self, session):
        patient = Patient(patient_code="TEST-PRED-AUDIT", age=65, sex="Male")
        session.add(patient)
        session.flush()

        assessment = Assessment(patient_id=patient.id)
        session.add(assessment)
        session.flush()

        target_def = "Coronary artery disease presence (num > 0) defined as >=50% diameter stenosis in major vessels"
        features_snapshot = {"age": 65, "sex": "Male", "trestbps": 150.0, "chol": 260.0}
        explanation_snapshot = {"top_positive": ["trestbps", "chol"], "method": "perturbation"}

        prediction = ModelPrediction(
            assessment_id=assessment.id,
            task_name="coronary_artery_disease",
            model_name="Heart Disease Coronary Artery Disease Classifier",
            model_version="1.0.0",
            target_definition=target_def,
            predicted_class_id=1,
            predicted_class_label="Coronary Artery Disease Present (>=50% stenosis)",
            raw_score=0.8842,
            calibrated_probability=0.8842,
            is_probability_calibrated=True,
            decision_threshold=0.5,
            score_type="calibrated_probability",
            input_features_snapshot=features_snapshot,
            explanation_snapshot=explanation_snapshot,
            clinical_prototype_disclaimer="Research prototype only.",
        )
        session.add(prediction)
        session.commit()

        pred_record = ModelPrediction.query.filter_by(assessment_id=assessment.id).first()
        assert pred_record is not None
        assert pred_record.target_definition == target_def
        assert pred_record.model_version == "1.0.0"
        assert pred_record.predicted_class_id == 1
        assert pred_record.is_probability_calibrated is True
        assert pred_record.input_features_snapshot["age"] == 65
        assert "top_positive" in pred_record.explanation_snapshot

    def test_seeder_creates_all_five_synthetic_scenarios(self, app):
        with app.app_context():
            counts = seed_synthetic_data(app)
            assert counts["patients"] == 5
            assert counts["assessments"] == 5
            assert counts["symptoms"] == 5
            assert counts["vitals"] == 5
            assert counts["documents"] >= 1
            assert counts["lab_measurements"] >= 5
            assert counts["predictions"] >= 3

            # Verify specific scenarios are queryable
            cad_pt = Patient.query.filter_by(patient_code="DEMO-PT-CAD-001").first()
            assert cad_pt is not None
            assert cad_pt.age == 58

            hf_pt = Patient.query.filter_by(patient_code="DEMO-PT-HF-002").first()
            assert hf_pt is not None
            assert hf_pt.assessments[0].symptoms.orthopnea is True

            emerg_pt = Patient.query.filter_by(patient_code="DEMO-PT-EMERG-004").first()
            assert emerg_pt is not None
            assert emerg_pt.assessments[0].emergency_escalation_level == "EMERGENCY_IMMEDIATE_911"
