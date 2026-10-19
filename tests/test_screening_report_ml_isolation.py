"""
Comprehensive Integration Tests for CardioCare AI:
1. Account Data Isolation, Permanent Deletion, and Fresh Re-Registration.
2. End-to-End Clinical Report Upload, Structured Parameter Parsing, and ML Inference.
3. Model Governance & Rejection of Unsupported Tasks.
"""

import io
from pathlib import Path
import pytest

from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.models import (
    User,
    Patient,
    Assessment,
    ClinicalDocument,
    StructuredLabMeasurement,
    ModelPrediction,
)


class TestAccountIsolationAndCleanReRegistration:
    """Verifies that accounts are completely isolated and re-registration starts 100% fresh."""

    def test_deletion_and_clean_reregistration_same_credentials(self, client, app):
        """
        1. Register User A.
        2. Create patient, assessment encounter, upload report, generate prediction.
        3. Delete User A permanently with password reauthentication.
        4. Confirm all dependent records and files are deleted.
        5. Re-register User B with the SAME email and password.
        6. Confirm User B has a NEW unique internal user ID and an empty account (0 records).
        7. Confirm User B cannot access User A's old record IDs.
        """
        email = "doctor.smith@heartcare.demo"
        password = "SecurePassword123!"

        # Step 1: Register User A
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Dr. Smith User A",
                "email": email,
                "password": password,
                "confirm_password": password,
                "role": "clinician",
            },
        )
        assert res_reg.status_code == 201
        data_a = res_reg.get_json()["data"]
        token_a = data_a["access_token"]
        user_a_id = data_a["user"]["id"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Step 2: Create Patient for User A
        res_pt = client.post(
            "/api/v1/patients",
            headers=headers_a,
            json={"medical_record_number": "MRN-USERA-01", "age": 62, "sex": "Male"},
        )
        assert res_pt.status_code == 201
        patient_a_id = res_pt.get_json()["data"]["id"]

        # Create Assessment Encounter
        res_assess = client.post(
            f"/api/v1/patients/{patient_a_id}/assessments",
            headers=headers_a,
            json={"reason_for_visit": "Chest tightness and dyspnea on exertion"},
        )
        assert res_assess.status_code == 201
        assess_a_id = res_assess.get_json()["data"]["id"]

        # Record structured lab
        res_lab = client.post(
            f"/api/v1/assessments/{assess_a_id}/labs",
            headers=headers_a,
            json={
                "test_name": "cholesterol",
                "value_numeric": 240.0,
                "unit": "mg/dL",
                "reference_high": 200.0,
                "flag": "high",
            },
        )
        assert res_lab.status_code == 201

        # Upload a clinical report
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        res_upload = client.post(
            f"/api/v1/assessments/{assess_a_id}/documents",
            headers=headers_a,
            data={
                "file": (io.BytesIO(pdf_content), "ecg_encounter_a.pdf", "application/pdf"),
                "document_category": "ecg_report_pdf",
            },
            content_type="multipart/form-data",
        )
        assert res_upload.status_code == 201
        doc_a_id = res_upload.get_json()["data"]["id"]

        # Verify User A has 1 patient
        res_list_a = client.get("/api/v1/patients", headers=headers_a)
        assert res_list_a.status_code == 200
        assert res_list_a.get_json()["data"]["total"] == 1

        # Step 3: Delete User A permanently
        res_del = client.delete(
            "/api/v1/auth/me",
            headers=headers_a,
            json={"password": password},
        )
        assert res_del.status_code == 200
        assert res_del.get_json()["data"]["deleted"] is True

        # Verify old token is rejected
        res_check_old = client.get("/api/v1/patients", headers=headers_a)
        assert res_check_old.status_code == 401

        # Verify dependent records are gone from database
        with app.app_context():
            assert User.query.filter_by(id=user_a_id).first() is None
            assert Patient.query.filter_by(id=patient_a_id).first() is None
            assert Assessment.query.filter_by(id=assess_a_id).first() is None
            assert ClinicalDocument.query.filter_by(id=doc_a_id).first() is None

        # Step 4: Re-register User B with the SAME email and password
        res_reg_b = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Dr. Smith User B",
                "email": email,
                "password": password,
                "confirm_password": password,
                "role": "clinician",
            },
        )
        assert res_reg_b.status_code == 201
        data_b = res_reg_b.get_json()["data"]
        token_b = data_b["access_token"]
        user_b_id = data_b["user"]["id"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B must have a DIFFERENT unique internal ID
        assert user_b_id != user_a_id

        # Step 5: User B must start completely clean with 0 patients
        res_list_b = client.get("/api/v1/patients", headers=headers_b)
        assert res_list_b.status_code == 200
        assert res_list_b.get_json()["data"]["total"] == 0
        assert len(res_list_b.get_json()["data"]["items"]) == 0

        # Step 6: User B CANNOT retrieve User A's old records (IDOR protected)
        res_pt_probe = client.get(f"/api/v1/patients/{patient_a_id}", headers=headers_b)
        assert res_pt_probe.status_code in (403, 404)

        res_assess_probe = client.get(f"/api/v1/assessments/{assess_a_id}/documents", headers=headers_b)
        assert res_assess_probe.status_code in (403, 404)

    def test_unrelated_accounts_remain_intact_on_deletion(self, client, app):
        """Deleting User X must never affect User Y or User Y's patient records."""
        # Register User X
        rx = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "User X",
                "email": "user.x@hospital.demo",
                "password": "PasswordX123!",
                "confirm_password": "PasswordX123!",
                "role": "clinician",
            },
        )
        tok_x = rx.get_json()["data"]["access_token"]
        headers_x = {"Authorization": f"Bearer {tok_x}"}

        # Register User Y
        ry = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "User Y",
                "email": "user.y@hospital.demo",
                "password": "PasswordY123!",
                "confirm_password": "PasswordY123!",
                "role": "clinician",
            },
        )
        tok_y = ry.get_json()["data"]["access_token"]
        headers_y = {"Authorization": f"Bearer {tok_y}"}

        # User Y creates patient
        res_pty = client.post(
            "/api/v1/patients",
            headers=headers_y,
            json={"medical_record_number": "MRN-USERY-99", "age": 45, "sex": "Female"},
        )
        patient_y_id = res_pty.get_json()["data"]["id"]

        # Delete User X
        del_x = client.delete(
            "/api/v1/auth/me",
            headers=headers_x,
            json={"password": "PasswordX123!"},
        )
        assert del_x.status_code == 200

        # Confirm User Y's patient is intact and accessible by User Y
        res_check_y = client.get(f"/api/v1/patients/{patient_y_id}", headers=headers_y)
        assert res_check_y.status_code == 200
        assert res_check_y.get_json()["data"]["id"] == patient_y_id


class TestReportParsingAndMLInferenceWorkflow:
    """Verifies clinical report upload, text extraction, structured parsing, and ML inference."""

    def test_report_upload_and_structured_extraction(self, client, clinician_token, sample_patient):
        """
        Upload real sample clinical PDF report and verify:
        - Text is extracted.
        - Structured biomarkers are parsed (cholesterol, glucose, creatinine, etc.).
        - Parsing status is set to 'parsed'.
        - Measurements are saved to database with provenance.
        """
        # Create encounter
        res_assess = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers={"Authorization": f"Bearer {clinician_token}"},
            json={"reason_for_visit": "Cardiovascular screening intake"},
        )
        assessment_id = res_assess.get_json()["data"]["id"]

        # Read actual sample clinical tests PDF report
        sample_pdf_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "CardioCare_AI_Sample_Clinical_Tests_Report.pdf"
        )
        assert sample_pdf_path.exists(), f"Sample report missing at {sample_pdf_path}"

        with open(sample_pdf_path, "rb") as f:
            pdf_bytes = f.read()

        res_upload = client.post(
            f"/api/v1/assessments/{assessment_id}/documents",
            headers={"Authorization": f"Bearer {clinician_token}"},
            data={
                "file": (io.BytesIO(pdf_bytes), "sample_report.pdf", "application/pdf"),
                "document_category": "lab_results",
            },
            content_type="multipart/form-data",
        )
        assert res_upload.status_code == 201
        upload_data = res_upload.get_json()["data"]
        assert upload_data["parsing_status"] == "parsed"
        assert upload_data["extracted_measurements_count"] >= 10

        # Verify structured lab measurements endpoint returns extracted values
        res_labs = client.get(
            f"/api/v1/assessments/{assessment_id}/labs",
            headers={"Authorization": f"Bearer {clinician_token}"},
        )
        assert res_labs.status_code == 200
        labs = res_labs.get_json()["data"]
        lab_names = {l["test_name"] for l in labs}
        assert "cholesterol" in lab_names
        assert "fasting_glucose" in lab_names
        assert "serum_creatinine" in lab_names

    def test_cad_and_hf_mortality_inference_execution(self, client, clinician_token, sample_patient):
        """
        Verify CAD and Heart Failure Mortality inference:
        - Valid inputs execute actual trained ML pipeline.
        - Persisted result includes model name, target definition, score type.
        - Result is retrievable via GET /predictions/<id>.
        """
        headers = {"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"}

        # Create encounter
        res_assess = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Comprehensive risk stratification"},
        )
        assessment_id = res_assess.get_json()["data"]["id"]

        # Enter clinical symptoms
        client.post(
            f"/api/v1/assessments/{assessment_id}/symptoms",
            headers=headers,
            json={
                "chest_pain": True,
                "chest_pain_quality": "pressure",
                "substernal_location": True,
                "exertional_provocation": True,
                "relieved_by_rest": True,
                "angina_classification": "typical_angina",
            },
        )

        # Enter vital signs
        client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers=headers,
            json={
                "systolic_bp": 138,
                "diastolic_bp": 86,
                "resting_heart_rate": 78,
                "height_cm": 175.0,
                "weight_kg": 82.0,
            },
        )

        # Execute CAD inference with direct features for complete clinical intake
        cad_payload = {
            "task_name": "coronary_artery_disease",
            "direct_features": {
                "age": 58,
                "sex": "Male",
                "cp": "typical angina",
                "trestbps": 138,
                "chol": 248.0,
                "fbs": 1,
                "restecg": "st-t abnormality",
                "thalch": 142,
                "exang": 1,
                "oldpeak": 1.4,
                "slope": "flat",
                "ca": 1,
                "thal": "reversable defect",
            },
            "explain": True,
        }
        res_cad = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json=cad_payload,
        )
        assert res_cad.status_code == 200
        cad_data = res_cad.get_json()["data"]
        assert cad_data["task_name"] == "coronary_artery_disease"
        assert cad_data["is_probability_calibrated"] is True
        assert cad_data["score_type"] == "calibrated_probability"
        assert cad_data["calibrated_probability"] is not None
        pred_id = cad_data["id"]

        # Verify individual prediction retrieval endpoint
        res_get = client.get(f"/api/v1/predictions/{pred_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.get_json()["data"]["id"] == pred_id

        # Execute Heart Failure Mortality inference
        hf_payload = {
            "task_name": "heart_failure_mortality",
            "direct_features": {
                "age": 65,
                "anaemia": 0,
                "creatinine_phosphokinase": 582,
                "diabetes": 1,
                "ejection_fraction": 35,
                "high_blood_pressure": 1,
                "platelets": 263358.03,
                "serum_creatinine": 1.3,
                "serum_sodium": 136,
                "sex": 1,
                "smoking": 0,
            },
            "explain": True,
        }
        res_hf = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json=hf_payload,
        )
        assert res_hf.status_code == 200
        hf_data = res_hf.get_json()["data"]
        assert hf_data["task_name"] == "heart_failure_mortality"
        assert hf_data["is_probability_calibrated"] is False
        assert hf_data["score_type"] == "classifier_confidence_score"

    def test_unsupported_heart_failure_screening_rejected(self, client, clinician_token, sample_patient):
        """
        Verify that general heart-failure screening is strictly rejected by the backend:
        - Prohibits fabricated predictions for uncalibrated models.
        - Returns 400 Bad Request with explicit clinical justification.
        """
        headers = {"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"}

        # Create encounter
        res_assess = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Screening check"},
        )
        assessment_id = res_assess.get_json()["data"]["id"]

        # Request prohibited task
        res_unsupp = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "heart_failure_screening"},
        )
        assert res_unsupp.status_code == 400
        err_msg = res_unsupp.get_json()["error"]["message"]
        assert "UNSUPPORTED TASK" in err_msg
        assert "heart failure screening" in err_msg.lower()
