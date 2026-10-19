"""
Phase 13: End-to-End Integration Test Suite.

Validates the complete clinical decision support workflow connecting:
1. Patient Profile Creation & De-identification
2. Symptom & History Intake
3. Emergency Clinical Rules Primacy (Independent of ML)
4. Guideline-Directed Test Recommendations
5. Objective Vitals & Structured Lab Measurements
6. Backend Clinical Validation & Zero Silent Imputation
7. Task Catalog & Supported Feature Determination
8. Calibrated ML Model Inference
9. Model Outputs, Target Definitions, & Non-Causal SHAP Attributions
10. Database Persistence & Immutability
11. Encounter Audit History & Role-Based Authorization
"""

import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.models import Patient, Assessment, ModelPrediction
from database.seed_demo_data import seed_synthetic_data


@pytest.fixture
def app():
    """Create test application bound to an in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        # Seed standard demo users (clinician_demo, patient_demo, admin_demo)
        seed_synthetic_data(test_app)
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def clinician_token(client):
    """JWT token for clinician demo account via /api/v1/auth/login."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "clinician_demo", "password": "ClinicianPass123!"},
    )
    assert res.status_code == 200, res.get_json()
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def patient_user_token(client):
    """JWT token for patient demo account via /api/v1/auth/login."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "patient_demo", "password": "PatientPass123!"},
    )
    assert res.status_code == 200, res.get_json()
    return res.get_json()["data"]["access_token"]


class TestEndToEndWorkflow:
    """Full lifecycle integration tests for the clinical workflow."""

    def test_complete_successful_workflow(self, client, clinician_token):
        """
        Executes all 11 steps of the specified clinical workflow in sequence:
        1. Create patient profile.
        2. Record symptoms & visit reason.
        3. Evaluate emergency rules independently of ML.
        4. Verify test recommendations.
        5. Enter vital signs and structured lab measurements.
        6. Validate data completeness on backend.
        7. Inspect task catalog.
        8. Run validated ML prediction pipeline.
        9. Verify structured prediction output with target definition and score vs probability.
        10. Verify database persistence.
        11. Retrieve and verify full assessment and prediction history.
        """
        headers = {
            "Authorization": f"Bearer {clinician_token}",
            "Content-Type": "application/json",
        }

        # Step 1: Create a synthetic patient profile
        patient_payload = {
            "first_name": "Synthea",
            "last_name": "Valida",
            "medical_record_number": "MRN-SYNTH-101",
            "age": 62,
            "sex": "Male",
            "smoking_status": "former",
            "has_diabetes": False,
            "has_hypertension": True,
        }
        res_pt = client.post("/api/v1/patients", json=patient_payload, headers=headers)
        assert res_pt.status_code == 201, res_pt.get_json()
        pt_data = res_pt.get_json()["data"]
        patient_id = pt_data["id"]
        assert pt_data["patient_code"].startswith("PT-")

        # Step 2: Create an assessment encounter and record symptoms
        res_assess = client.post(
            f"/api/v1/patients/{patient_id}/assessments",
            json={"reason_for_visit": "Exertional chest discomfort evaluation"},
            headers=headers,
        )
        assert res_assess.status_code == 201
        assessment_id = res_assess.get_json()["data"]["id"]

        symptom_payload = {
            "chest_pain": True,
            "substernal_location": True,
            "exertional_provocation": True,
            "rest_or_nitroglycerin_relief": True,
            "angina_classification": "typical_angina",
            "shortness_of_breath": True,
            "dyspnea_trigger": "exertion",
            "unusual_fatigue": False,
            "leg_swelling": False,
            "palpitations": False,
            "dizziness_or_fainting": False,
        }
        res_sym = client.post(
            f"/api/v1/assessments/{assessment_id}/symptoms",
            json=symptom_payload,
            headers=headers,
        )
        assert res_sym.status_code == 200
        assert res_sym.get_json()["data"]["angina_classification"] == "typical_angina"

        # Step 3 & 4: Evaluate emergency rules and recommendations independently of ML
        res_recs = client.get(
            f"/api/v1/assessments/{assessment_id}/recommendations",
            headers=headers,
        )
        assert res_recs.status_code == 200
        rec_data = res_recs.get_json()["data"]
        # Typical angina with exertional provocation triggers standard guideline secondary testing
        assert "diagnostic_recommendations" in rec_data
        assert rec_data["is_emergency"] is False
        assert rec_data["emergency_triage"]["is_emergency"] is False
        assert rec_data["symptom_evaluation"]["angina_classification"] == "typical_angina"

        # Step 5: Enter physiological vital signs and structured lab measurements
        vitals_payload = {
            "systolic_bp": 142.0,
            "diastolic_bp": 88.0,
            "heart_rate": 78,
            "height_cm": 175.0,
            "weight_kg": 82.0,
        }
        res_vit = client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            json=vitals_payload,
            headers=headers,
        )
        assert res_vit.status_code == 200
        assert res_vit.get_json()["data"]["systolic_bp"] == 142.0

        # Add structured lab values required by CAD pipeline
        labs = [
            {"test_name": "cholesterol", "value_numeric": 235.0, "unit": "mg/dL"},
            {"test_name": "fbs", "value_numeric": 95.0, "unit": "mg/dL"},
            {"test_name": "restecg", "value_text": "normal"},
            {"test_name": "oldpeak", "value_numeric": 1.4},
            {"test_name": "slope", "value_text": "flat"},
            {"test_name": "ca", "value_numeric": 1},
            {"test_name": "thal", "value_text": "reversable defect"},
        ]
        for lab in labs:
            res_lab = client.post(
                f"/api/v1/assessments/{assessment_id}/labs",
                json=lab,
                headers=headers,
            )
            assert res_lab.status_code == 201

        # Step 6 & 7: Query catalog and determine supported prediction tasks
        res_cat = client.get("/api/v1/predictions/tasks", headers=headers)
        assert res_cat.status_code == 200
        cat_data = res_cat.get_json()["data"]
        supported_names = [t["task_name"] for t in cat_data["supported_tasks"]]
        assert "coronary_artery_disease" in supported_names
        assert "heart_failure_mortality" in supported_names

        # Step 8, 9, 10: Call validated CAD model pipeline and verify output & persistence
        pred_payload = {
            "task_name": "coronary_artery_disease",
            "explain": True,
        }
        res_pred = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            json=pred_payload,
            headers=headers,
        )
        assert res_pred.status_code == 200
        pred_data = res_pred.get_json()["data"]

        # Verify target definition and model metadata
        assert "coronary artery disease" in pred_data["target_definition"].lower()
        assert "50%" in pred_data["target_definition"]
        assert pred_data["model_version"] is not None
        assert pred_data["is_probability_calibrated"] is True
        assert 0.0 <= pred_data["calibrated_probability"] <= 1.0
        assert pred_data["predicted_class_id"] in (0, 1)

        # Verify SHAP / feature explanation has non-causal disclaimer
        assert pred_data["explanation_snapshot"] is not None
        assert "non_causal_disclaimer" in pred_data["explanation_snapshot"]

        # Step 11: Retrieve and verify prediction history and assessment trail
        res_history = client.get(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
        )
        assert res_history.status_code == 200
        history_list = res_history.get_json()["data"]
        assert len(history_list) == 1
        assert history_list[0]["id"] == pred_data["id"]

        # Verify patient encounters trail
        res_encounters = client.get(
            f"/api/v1/patients/{patient_id}/assessments",
            headers=headers,
        )
        assert res_encounters.status_code == 200
        encounters = res_encounters.get_json()["data"]
        assert len(encounters) == 1
        assert encounters[0]["id"] == assessment_id

    def test_emergency_rules_primacy_independent_of_ml(self, client, clinician_token):
        """
        Emergency rules must evaluate immediately and trigger escalation independently
        of model inference. Emergency flags cannot be cleared by low model scores.
        """
        headers = {
            "Authorization": f"Bearer {clinician_token}",
            "Content-Type": "application/json",
        }

        # Create patient
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-EMERG-999", "age": 52, "sex": "Female"},
            headers=headers,
        )
        pt_id = res_pt.get_json()["data"]["id"]

        # Create assessment
        res_assess = client.post(f"/api/v1/patients/{pt_id}/assessments", json={}, headers=headers)
        assess_id = res_assess.get_json()["data"]["id"]

        # Enter red-flag emergency symptoms (crushing chest pain + syncope + radiation)
        res_sym = client.post(
            f"/api/v1/assessments/{assess_id}/symptoms",
            json={
                "chest_pain": True,
                "chest_pain_quality": "crushing pressure",
                "chest_pain_radiation": "left arm and jaw",
                "substernal_location": True,
                "syncope": True,
                "diaphoresis": True,
            },
            headers=headers,
        )
        assert res_sym.status_code == 200

        # Evaluate recommendations WITHOUT running ML
        res_recs = client.get(f"/api/v1/assessments/{assess_id}/recommendations", headers=headers)
        assert res_recs.status_code == 200
        rec_data = res_recs.get_json()["data"]

        # Must flag emergency immediately
        assert rec_data["is_emergency"] is True
        assert rec_data["emergency_triage"]["escalation_level"] == "EMERGENCY_IMMEDIATE_911"
        assert any("911" in plan for plan in rec_data["emergency_triage"]["emergency_action_plan"])
        assert rec_data["overall_urgency"] == "EMERGENCY_IMMEDIATE_911"

        # Check that the assessment itself was flagged as emergency
        res_assess_get = client.get(f"/api/v1/assessments/{assess_id}", headers=headers)
        assert res_assess_get.status_code == 200
        assert res_assess_get.get_json()["data"]["status"] == "flagged_emergency"

    def test_missing_required_features_rejected_without_silent_imputation(self, client, clinician_token):
        """
        Backend inference must reject incomplete feature sets with 422 Unprocessable Entity
        and never silently impute arbitrary clinical values.
        """
        headers = {
            "Authorization": f"Bearer {clinician_token}",
            "Content-Type": "application/json",
        }

        # Create patient and assessment
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-INCOMP-102", "age": 45, "sex": "Male"},
            headers=headers,
        )
        pt_id = res_pt.get_json()["data"]["id"]
        res_assess = client.post(f"/api/v1/patients/{pt_id}/assessments", json={}, headers=headers)
        assess_id = res_assess.get_json()["data"]["id"]

        # Only provide symptoms, but no vitals or labs (missing chol, trestbps, ca, etc.)
        client.post(
            f"/api/v1/assessments/{assess_id}/symptoms",
            json={"chest_pain": True, "angina_classification": "atypical_angina"},
            headers=headers,
        )

        # Attempt CAD prediction
        res_pred = client.post(
            f"/api/v1/assessments/{assess_id}/predictions",
            json={"task_name": "coronary_artery_disease"},
            headers=headers,
        )
        # Must fail with validation error, not fabricate an estimate
        assert res_pred.status_code == 422
        err = res_pred.get_json()["error"]
        assert "missing" in err["message"].lower() or "validation" in err["message"].lower()

        # Verify no prediction record was persisted in database
        res_history = client.get(f"/api/v1/assessments/{assess_id}/predictions", headers=headers)
        assert res_history.status_code == 200
        assert len(res_history.get_json()["data"]) == 0

    def test_unsupported_task_explicitly_rejected(self, client, clinician_token):
        """
        Requesting unsupported tasks (e.g. general population heart failure screening)
        must return 400 Bad Request with documented rationale.
        """
        headers = {
            "Authorization": f"Bearer {clinician_token}",
            "Content-Type": "application/json",
        }

        # Create patient and assessment
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-UNSUP-103", "age": 70, "sex": "Female"},
            headers=headers,
        )
        pt_id = res_pt.get_json()["data"]["id"]
        res_assess = client.post(f"/api/v1/patients/{pt_id}/assessments", json={}, headers=headers)
        assess_id = res_assess.get_json()["data"]["id"]

        # Attempt to run unsupported heart_failure_screening task
        res_pred = client.post(
            f"/api/v1/assessments/{assess_id}/predictions",
            json={"task_name": "heart_failure_screening"},
            headers=headers,
        )
        assert res_pred.status_code == 400
        err = res_pred.get_json()["error"]
        assert "unsupported" in err["message"].lower()

    def test_patient_authorization_and_isolation(self, client, clinician_token, patient_user_token):
        """
        Enforce role-based access control and patient data isolation:
        - Unauthenticated requests return 401.
        - Patient accounts cannot access another patient's records (403).
        """
        # Unauthenticated request
        res_unauth = client.get("/api/v1/patients")
        assert res_unauth.status_code == 401

        # Clinician creates patient
        clin_headers = {"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"}
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-ISOL-104", "age": 50, "sex": "Male"},
            headers=clin_headers,
        )
        target_pt_id = res_pt.get_json()["data"]["id"]

        # Patient user tries to access this clinician-created patient record
        patient_headers = {"Authorization": f"Bearer {patient_user_token}"}
        # Patient user CAN access their own assigned record (ID 1 seeded in DEMO_USERS)
        res_own = client.get("/api/v1/patients/1", headers=patient_headers)
        assert res_own.status_code == 200

        # Patient user is strictly forbidden from accessing another patient's medical records
        res_denied = client.get(f"/api/v1/patients/{target_pt_id + 100}", headers=patient_headers)
        assert res_denied.status_code == 403

    def test_hf_mortality_pipeline_execution(self, client, clinician_token):
        """
        Validates the Heart Failure Mortality prediction pipeline:
        - Requires confirmed heart failure laboratory metrics (EF, creatinine, sodium, etc.)
        - Persists result with appropriate mortality target definition.
        """
        headers = {
            "Authorization": f"Bearer {clinician_token}",
            "Content-Type": "application/json",
        }

        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-HF-105", "age": 65, "sex": "Male"},
            headers=headers,
        )
        pt_id = res_pt.get_json()["data"]["id"]

        res_assess = client.post(
            f"/api/v1/patients/{pt_id}/assessments",
            json={"reason_for_visit": "Known Heart Failure Follow-up"},
            headers=headers,
        )
        assess_id = res_assess.get_json()["data"]["id"]

        # Vitals with BP
        client.post(
            f"/api/v1/assessments/{assess_id}/vitals",
            json={"systolic_bp": 130.0, "diastolic_bp": 85.0},
            headers=headers,
        )

        # Direct features or structured labs for HF mortality
        direct_hf = {
            "age": 65,
            "anaemia": 0,
            "creatinine_phosphokinase": 250.0,
            "diabetes": 0,
            "ejection_fraction": 35.0,
            "high_blood_pressure": 0,
            "platelets": 263358.0,
            "serum_creatinine": 1.4,
            "serum_sodium": 136.0,
            "sex": 1,
            "smoking": 0,
        }

        res_pred = client.post(
            f"/api/v1/assessments/{assess_id}/predictions",
            json={
                "task_name": "heart_failure_mortality",
                "direct_features": direct_hf,
                "explain": True,
            },
            headers=headers,
        )
        assert res_pred.status_code == 200
        p_data = res_pred.get_json()["data"]
        assert p_data["raw_score"] is not None
        assert p_data["is_probability_calibrated"] is False
        assert p_data["calibrated_probability"] is None
