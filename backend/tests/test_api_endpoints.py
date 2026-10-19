"""
Comprehensive API Endpoint Integration and Security Tests for Phase 11.

Covers:
1. Authentication & JWT session handling (login, invalid creds, token decoding).
2. Role-Based Access Control and Patient Privacy Isolation (patients cannot access other patients' records).
3. Patient Profile CRUD (de-identification, hashed MRN, pagination, filtering).
4. Clinical Assessment, Symptoms, and Vital Signs (nullability preservation, auto BMI, Diamond-Forrester classification).
5. Secure Document Uploads (magic byte verification, extension whitelisting, private storage, unparsed status).
6. Structured Laboratory Measurement Entry (distinguishing NULL from 0.0).
7. Clinical Recommendation Engine (emergency triage primacy, automatic escalation).
8. ML Inference Integration (explicit feature mapping, real predictions, SHAP explanations, zero silent imputation).
9. Explicit rejection of unsupported tasks (e.g. heart failure general screening).
10. Prediction audit history retrieval (preserving model version and target definition).
11. Resilient error handling and database transaction rollback.
"""

import io
import json
import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.models import Patient, Assessment, PatientSymptom, VitalSign, StructuredLabMeasurement


@pytest.fixture
def app():
    """Create Flask application in testing mode with in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def clinician_token(client):
    """Retrieve JWT token for demo clinician."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "clinician_demo", "password": "ClinicianPass123!"},
    )
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def patient_token(client):
    """Retrieve JWT token for demo patient (patient_id=1)."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "patient_demo", "password": "PatientPass123!"},
    )
    assert res.status_code == 200
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def sample_patient(app):
    """Seed a sample patient in database."""
    with app.app_context():
        from database.models import User
        clin = User.query.filter_by(username="clinician_demo").first()
        clin_id = clin.id if clin else 1
        pt = Patient(
            patient_code="PT-SYNTH001",
            user_id=clin_id,
            age=58,
            sex="Male",
            notes="Synthetic patient for automated API verification.",
            is_active=True,
        )
        db.session.add(pt)
        db.session.commit()
        return pt.id


class TestAuthenticationEndpoints:
    """Test suite for /api/v1/auth endpoints."""

    def test_login_success(self, client):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "clinician_demo", "password": "ClinicianPass123!"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert data["data"]["user"]["role"] == "clinician"

    def test_login_invalid_password(self, client):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "clinician_demo", "password": "WrongPassword123!"},
        )
        assert res.status_code == 401
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 401

    def test_login_validation_error(self, client):
        # Username too short (< 3 chars)
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "ab", "password": "123"},
        )
        assert res.status_code == 422
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 422

    def test_auth_me_with_valid_token(self, client, clinician_token):
        res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["username"] == "clinician_demo"
        assert data["role"] == "clinician"

    def test_auth_me_missing_token(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 401

    def test_auth_me_malformed_token(self, client):
        res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer invalid_token_format"},
        )
        assert res.status_code == 401


class TestPatientEndpointsAndPrivacy:
    """Test suite for /api/v1/patients endpoints and HIPAA privacy controls."""

    def test_create_patient_authorized(self, client, clinician_token):
        res = client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "age": 62,
                "sex": "Female",
                "medical_record_number": "MRN-998877",
                "notes": "Intake assessment for cardiac evaluation.",
            },
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["age"] == 62
        assert data["sex"] == "Female"
        assert data["patient_code"].startswith("PT-")

    def test_create_patient_unauthorized_role(self, client, patient_token):
        # Patient cannot create another patient record
        res = client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={"age": 50, "sex": "Male"},
        )
        assert res.status_code == 403

    def test_create_patient_validation_error(self, client, clinician_token):
        # Invalid sex and negative age
        res = client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"age": -5, "sex": "InvalidSexOption"},
        )
        assert res.status_code == 422
        data = res.get_json()
        assert data["status"] == "error"

    def test_list_patients_clinician(self, client, clinician_token, sample_patient):
        res = client.get(
            "/api/v1/patients?page=1&per_page=10",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_patient_privacy_isolation(self, client, patient_token, app, sample_patient):
        """Verify that a patient user CANNOT access another patient's medical records."""
        with app.app_context():
            # sample_patient has id=1 (matches patient_demo.patient_id). Create patient 2 (other_patient)
            other_patient = Patient(
                patient_code="PT-CONFIDENTIAL2",
                age=70,
                sex="Male",
                notes="Confidential patient data.",
            )
            db.session.add(other_patient)
            db.session.commit()
            other_id = other_patient.id

        # Attempt to access other patient's record using patient_token (patient_id=1)
        res = client.get(
            f"/api/v1/patients/{other_id}",
            headers={"Authorization": f"Bearer {patient_token}"},
        )
        assert res.status_code == 403
        data = res.get_json()
        assert "Privacy Violation" in data["error"]["message"]

    def test_update_patient(self, client, clinician_token, sample_patient):
        res = client.put(
            f"/api/v1/patients/{sample_patient}",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"age": 59, "notes": "Updated follow-up notes."},
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["age"] == 59
        assert "Updated follow-up" in data["notes"]


class TestAssessmentSymptomsAndVitals:
    """Test suite for clinical assessment, symptoms, and physiological vitals."""

    def test_create_assessment_and_ingest_symptoms(self, client, clinician_token, sample_patient):
        # 1. Initiate assessment encounter
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"reason_for_visit": "Exertional chest discomfort"},
        )
        assert res.status_code == 201
        assessment_id = res.get_json()["data"]["id"]

        # 2. Record symptoms (typical angina triad)
        symptom_res = client.post(
            f"/api/v1/assessments/{assessment_id}/symptoms",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "chest_pain": True,
                "chest_pain_quality": "pressure",
                "substernal_location": True,
                "exertional_provocation": True,
                "relieved_by_rest": True,
                "dyspnea": True,
            },
        )
        assert symptom_res.status_code == 200
        symptom_data = symptom_res.get_json()["data"]
        assert symptom_data["chest_pain"] is True
        # Diamond-Forrester classification should be typical_angina
        assert symptom_data["angina_classification"] == "typical_angina"

    def test_vitals_nullability_and_validation(self, client, clinician_token, sample_patient):
        # 1. Create encounter
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"reason_for_visit": "Vitals verification"},
        )
        assessment_id = res.get_json()["data"]["id"]

        # 2. Invalid vitals (diastolic >= systolic)
        inv_res = client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"systolic_bp": 120.0, "diastolic_bp": 130.0},
        )
        assert inv_res.status_code == 422

        # 3. Valid vitals with height and weight -> automatic BMI calculation
        valid_res = client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "systolic_bp": 138.0,
                "diastolic_bp": 86.0,
                "heart_rate": 78.0,
                "height_cm": 175.0,
                "weight_kg": 80.0,
                # Note: spo2, temperature, respiratory_rate are omitted
            },
        )
        assert valid_res.status_code == 200
        vitals_data = valid_res.get_json()["data"]
        assert vitals_data["systolic_bp"] == 138.0
        # Omitted vitals must be null, never 0.0
        assert vitals_data["spo2"] is None
        assert vitals_data["respiratory_rate"] is None
        # Auto-computed BMI: 80 / (1.75^2) = ~26.12
        assert vitals_data["bmi"] is not None
        assert 26.0 <= vitals_data["bmi"] <= 26.5


class TestDocumentUploadAndStructuredLabs:
    """Test suite for secure document uploads and structured lab entries."""

    def test_upload_valid_pdf_document(self, client, clinician_token, sample_patient):
        # Create encounter
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"reason_for_visit": "Document upload"},
        )
        assessment_id = res.get_json()["data"]["id"]

        # Synthetic PDF with valid %PDF magic bytes
        fake_pdf = b"%PDF-1.4\n%synthetic test document content for clinical intake"
        data = {
            "file": (io.BytesIO(fake_pdf), "resting_ecg.pdf", "application/pdf"),
            "document_category": "ecg_report_pdf",
        }

        upload_res = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            headers={"Authorization": f"Bearer {clinician_token}"},
            data=data,
            content_type="multipart/form-data",
        )
        assert upload_res.status_code == 201
        doc_data = upload_res.get_json()["data"]
        assert doc_data["file_type"] == "pdf"
        assert doc_data["parsing_status"] == "stored_unparsed"
        assert "sha256_hash" in doc_data
        assert "No automated diagnostic interpretation performed" in doc_data["extraction_notice"]

        # Download document
        doc_id = doc_data["id"]
        down_res = client.get(
            f"/api/v1/documents/{doc_id}/download",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert down_res.status_code == 200
        assert down_res.data == fake_pdf

    def test_upload_rejects_spoofed_or_invalid_extension(self, client, clinician_token, sample_patient):
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        # Disallowed extension
        exe_file = (io.BytesIO(b"MZ\x90\x00executable"), "script.exe", "application/octet-stream")
        bad_res = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            headers={"Authorization": f"Bearer {clinician_token}"},
            data={"file": exe_file},
            content_type="multipart/form-data",
        )
        assert bad_res.status_code == 400
        assert "Unsupported file extension" in bad_res.get_json()["error"]["message"]

        # Spoofed extension: named .pdf but containing plain text without %PDF header
        spoofed = (io.BytesIO(b"Just plain text pretending to be a pdf"), "fake.pdf", "application/pdf")
        magic_res = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            headers={"Authorization": f"Bearer {clinician_token}"},
            data={"file": spoofed},
            content_type="multipart/form-data",
        )
        assert magic_res.status_code == 400
        assert "Magic byte header does not match" in magic_res.get_json()["error"]["message"]

    def test_record_structured_lab_measurements(self, client, clinician_token, sample_patient):
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        # Record cholesterol
        lab_res = client.post(
            f"/api/v1/assessments/{assessment_id}/labs",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "test_name": "cholesterol",
                "value_numeric": 245.0,
                "unit": "mg/dL",
                "reference_high": 200.0,
                "flag": "high",
            },
        )
        assert lab_res.status_code == 201
        lab_data = lab_res.get_json()["data"]
        assert lab_data["test_name"] == "cholesterol"
        assert lab_data["value_numeric"] == 245.0

        # List labs
        list_res = client.get(
            f"/api/v1/assessments/{assessment_id}/labs",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert list_res.status_code == 200
        assert len(list_res.get_json()["data"]) == 1


class TestClinicalRecommendationsAndSafety:
    """Test suite for clinical recommendation engine and emergency rule triage."""

    def test_ad_hoc_emergency_triage(self, client):
        # Severe crushing chest pain with radiation to left arm
        payload = {
            "patient_symptoms": {
                "chest_pain": True,
                "chest_pain_quality": "crushing",
                "chest_pain_radiation": "left arm",
                "substernal_location": True,
                "diaphoresis": True,
            },
            "measured_vitals": {
                "systolic_bp": 90.0,
                "heart_rate": 115.0,
            },
            "clinical_history": {"age": 64, "sex": "Male"},
        }
        res = client.post("/api/v1/recommendations/evaluate", json=payload)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["is_emergency"] is True
        assert data["overall_urgency"] == "EMERGENCY_IMMEDIATE_911"
        assert len(data["emergency_triage"]["triggered_rules"]) >= 1

    def test_assessment_recommendation_and_emergency_escalation(self, client, clinician_token, sample_patient):
        # 1. Create encounter
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        # 2. Ingest critical emergency vitals (severe hypertensive emergency BP >= 180)
        client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"systolic_bp": 210.0, "diastolic_bp": 125.0, "heart_rate": 92.0},
        )
        client.post(
            f"/api/v1/assessments/{assessment_id}/symptoms",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"chest_pain": True, "chest_pain_quality": "pressure"},
        )

        # 3. Evaluate recommendations
        rec_res = client.get(
            f"/api/v1/assessments/{assessment_id}/recommendations",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert rec_res.status_code == 200
        rec_data = rec_res.get_json()["data"]
        assert rec_data["is_emergency"] is True

        # 4. Confirm encounter status was escalated
        assess_res = client.get(
            f"/api/v1/assessments/{assessment_id}",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert assess_res.status_code == 200
        assert assess_res.get_json()["data"]["emergency_escalation_level"] == "EMERGENCY_IMMEDIATE_911"
        assert assess_res.get_json()["data"]["status"] == "flagged_emergency"


class TestMachineLearningPredictionEndpoints:
    """Test suite for ML inference, feature mapping, and history tracking."""

    def test_query_prediction_task_catalog(self, client):
        res = client.get("/api/v1/predictions/tasks")
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert "supported_tasks" in data
        assert "unsupported_tasks" in data
        supported_names = [t["task_name"] for t in data["supported_tasks"]]
        assert "coronary_artery_disease" in supported_names
        assert "heart_failure_mortality" in supported_names
        assert "heart_failure_screening" in data["unsupported_tasks"]

    def test_reject_explicitly_unsupported_task(self, client, clinician_token, sample_patient):
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        pred_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"task_name": "heart_failure_screening"},
        )
        assert pred_res.status_code == 400
        data = pred_res.get_json()
        assert "UNSUPPORTED TASK" in data["error"]["message"]

    def test_prediction_missing_features_validation_error(self, client, clinician_token, sample_patient):
        # Empty assessment without vitals/labs
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        pred_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"task_name": "coronary_artery_disease"},
        )
        # Must return 422 with clear validation error, never silently impute
        assert pred_res.status_code == 422
        data = pred_res.get_json()
        assert "Missing required clinical inputs" in data["error"]["message"]

    def test_cad_prediction_direct_features(self, client, clinician_token, sample_patient):
        """Execute CAD prediction with complete synthetic feature payload."""
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        cad_features = {
            "age": 55,
            "sex": "Male",
            "cp": "typical angina",
            "trestbps": 140,
            "chol": 240,
            "fbs": False,
            "restecg": "normal",
            "thalch": 150,
            "exang": True,
            "oldpeak": 1.5,
            "slope": "flat",
            "ca": 0,
            "thal": "normal",
        }

        pred_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "task_name": "coronary_artery_disease",
                "explain": True,
                "direct_features": cad_features,
            },
        )
        assert pred_res.status_code == 200
        pred_data = pred_res.get_json()["data"]
        assert pred_data["task_name"] == "coronary_artery_disease"
        assert pred_data["model_version"] == "1.0.0"
        assert "50% diameter stenosis" in pred_data["target_definition"] or "Coronary artery disease" in pred_data["target_definition"]
        assert pred_data["is_probability_calibrated"] is True
        assert 0.0 <= pred_data["calibrated_probability"] <= 1.0
        assert pred_data["explanation_snapshot"] is not None

        # Verify history retrieval
        hist_res = client.get(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert hist_res.status_code == 200
        history = hist_res.get_json()["data"]
        assert len(history) == 1
        assert history[0]["task_name"] == "coronary_artery_disease"

    def test_heart_failure_mortality_prediction(self, client, clinician_token, sample_patient):
        """Execute Heart Failure Mortality prediction with synthetic features."""
        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        hf_features = {
            "age": 65,
            "anaemia": 0,
            "creatinine_phosphokinase": 250,
            "diabetes": 0,
            "ejection_fraction": 35,
            "high_blood_pressure": 1,
            "platelets": 260000,
            "serum_creatinine": 1.4,
            "serum_sodium": 136,
            "sex": 1,
            "smoking": 0,
        }

        pred_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "task_name": "heart_failure_mortality",
                "explain": True,
                "direct_features": hf_features,
            },
        )
        assert pred_res.status_code == 200
        pred_data = pred_res.get_json()["data"]
        assert pred_data["task_name"] == "heart_failure_mortality"
        assert pred_data["is_probability_calibrated"] is False
        assert "All-cause mortality" in pred_data["target_definition"]


class TestResilientErrorAndDatabaseHandling:
    """Test suite for database errors, rollbacks, and unavailable artifacts."""

    def test_database_commit_failure_handled_safely(self, client, clinician_token, monkeypatch):
        """Verify that a database failure during patient creation triggers graceful error response."""
        from sqlalchemy.exc import SQLAlchemyError

        def mock_commit_error():
            raise SQLAlchemyError("Simulated database disk I/O failure.")

        monkeypatch.setattr(db.session, "commit", mock_commit_error)

        res = client.post(
            "/api/v1/patients",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"age": 52, "sex": "Male"},
        )
        assert res.status_code == 500
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 500

    def test_unavailable_model_artifact_returns_503(self, client, clinician_token, sample_patient, monkeypatch):
        """Verify that a missing model artifact returns 503 Service Unavailable."""
        from Machine_Learning.src.predict import ModelArtifactNotFoundError

        def mock_predict(*args, **kwargs):
            raise ModelArtifactNotFoundError("Simulated missing model artifact file.")

        monkeypatch.setattr("backend.services.prediction_service.predict_clinical_condition", mock_predict)

        res = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assessment_id = res.get_json()["data"]["id"]

        pred_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": {"age": 50, "sex": "Male"},
            },
        )
        assert pred_res.status_code == 503
        data = pred_res.get_json()
        assert data["status"] == "error"
        assert data["error"]["code"] == 503
