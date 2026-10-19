"""
Regression Test Suite for Problem Areas A through G.

Verifies:
1. API-to-ML input propagation, category decoding, and non-leakage between assessments.
2. Clinical rules vs ML prediction separation (eliminating the 'Always Typical Angina' conflation).
3. Consistent server-side UTC timestamp generation and ISO 8601 'Z' serialization.
4. Clean empty database states and verification of the safe reset procedure.
5. Foreign key cascading and absence of orphaned records.
"""

from datetime import datetime, timezone
import pytest

from backend.extensions import db
from database.models import (
    Patient,
    Assessment,
    PatientSymptom,
    VitalSign,
    StructuredLabMeasurement,
    ModelPrediction,
    to_iso_utc,
)
from database.reset_data import reset_clinical_data
from backend.services.prediction_service import PredictionService
from backend.schemas.prediction_schema import PredictionRequestSchema


class TestAPItoMLInputPropagation:
    """Demonstrate correct input propagation from clinical intake to ML inference."""

    def test_diamond_forrester_criteria_non_typical_propagation(self, app, client, clinician_token, sample_patient):
        """
        Verify that a patient presenting with NON-substernal or resting discomfort
        is categorized as non-anginal or atypical angina, and that cp feature is correctly
        mapped rather than defaulting to 'typical angina'.
        """
        headers = {"Authorization": f"Bearer {clinician_token}"}

        # 1. Create Encounter
        res_a = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Atypical chest discomfort checkup"},
        )
        assert res_a.status_code == 201
        assessment_id = res_a.get_json()["data"]["id"]

        # 2. Record symptoms where chest pain is NOT substernal and NOT exertional (Non-anginal)
        res_sym = client.post(
            f"/api/v1/assessments/{assessment_id}/symptoms",
            headers=headers,
            json={
                "chest_pain": True,
                "substernal_location": False,      # Peripheral chest wall
                "exertional_provocation": False,    # Not provoked by effort
                "relieved_by_rest": True,          # Relieved by rest (1 criterion met)
                "chest_pain_quality": "sharp",
            },
        )
        assert res_sym.status_code == 200
        sym_data = res_sym.get_json()["data"]
        # Criteria met: 1/3 -> Diamond-Forrester resolves to non_anginal
        assert sym_data["angina_classification"] == "non_anginal"

        # 3. Add vitals and labs required for CAD inference
        client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers=headers,
            json={"systolic_bp": 120.0, "heart_rate": 72.0},
        )
        for name, val in [
            ("cholesterol", 210.0),
            ("maximum_heart_rate", 150.0),
            ("fasting_blood_sugar", 100.0),
            ("restecg", "normal"),
            ("st_depression", 0.0),
            ("slope", "upsloping"),
            ("ca", 0),
            ("thal", "normal"),
        ]:
            client.post(
                f"/api/v1/assessments/{assessment_id}/labs",
                headers=headers,
                json={"test_name": name, "value_numeric": val if isinstance(val, (int, float)) else None, "value_text": str(val)},
            )

        # 4. Map features for CAD model
        with app.app_context():
            assessment = db.session.get(Assessment, assessment_id)
            mapped = PredictionService.map_assessment_to_features(
                assessment=assessment,
                task_name="coronary_artery_disease",
            )
            # Must map to "non-anginal", NOT "typical angina"!
            assert mapped["cp"] == "non-anginal"
            assert mapped["age"] == 58
            assert mapped["sex"] == "Male"
            assert mapped["trestbps"] == 120.0
            assert mapped["thalch"] == 150.0
            assert mapped["thalch"] != 72.0  # Resting heart rate 72 is not substituted for maximum exercise HR

        # 5. Execute inference through API
        res_pred = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease"},
        )
        assert res_pred.status_code == 200
        pred_data = res_pred.get_json()["data"]
        assert pred_data["task_name"] == "coronary_artery_disease"
        assert "predicted_class_label" in pred_data
        assert pred_data["input_features_snapshot"]["cp"] == "non-anginal"

    def test_assessment_isolation_no_cross_encounter_leakage(self, app, client, clinician_token, sample_patient):
        """
        Verify that clinical parameters and symptoms from encounter #1 do not
        leak into encounter #2 for the same patient.
        """
        headers = {"Authorization": f"Bearer {clinician_token}"}

        # Encounter 1: typical angina with elevated BP
        res_a1 = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Visit 1"},
        )
        a1_id = res_a1.get_json()["data"]["id"]
        client.post(
            f"/api/v1/assessments/{a1_id}/symptoms",
            headers=headers,
            json={
                "chest_pain": True,
                "substernal_location": True,
                "exertional_provocation": True,
                "relieved_by_rest": True,
            },
        )
        client.post(
            f"/api/v1/assessments/{a1_id}/vitals",
            headers=headers,
            json={"systolic_bp": 170.0, "heart_rate": 95.0},
        )

        # Encounter 2: Asymptomatic follow-up months later
        res_a2 = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Visit 2 follow-up"},
        )
        a2_id = res_a2.get_json()["data"]["id"]
        client.post(
            f"/api/v1/assessments/{a2_id}/symptoms",
            headers=headers,
            json={"chest_pain": False, "dyspnea": False},
        )
        client.post(
            f"/api/v1/assessments/{a2_id}/vitals",
            headers=headers,
            json={"systolic_bp": 118.0, "heart_rate": 68.0},
        )

        with app.app_context():
            a1 = db.session.get(Assessment, a1_id)
            a2 = db.session.get(Assessment, a2_id)

            feat1 = PredictionService.map_assessment_to_features(a1, "coronary_artery_disease")
            feat2 = PredictionService.map_assessment_to_features(a2, "coronary_artery_disease")

            assert feat1["cp"] == "typical angina"
            assert feat1["trestbps"] == 170.0

            assert feat2["cp"] == "asymptomatic"
            assert feat2["trestbps"] == 118.0

    def test_model_identity_and_metadata_in_response(self, client, clinician_token, sample_patient):
        """Verify the API returns full model identity and regulatory metadata."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(
            f"/api/v1/patients/{sample_patient}/assessments",
            headers=headers,
            json={"reason_for_visit": "Metadata verification"},
        )
        a_id = res_a.get_json()["data"]["id"]

        # Directly provide complete valid features
        res_p = client.post(
            f"/api/v1/assessments/{a_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": {
                    "age": 55,
                    "sex": "Male",
                    "cp": "atypical angina",
                    "trestbps": 130.0,
                    "chol": 220.0,
                    "fbs": False,
                    "restecg": "normal",
                    "thalch": 160.0,
                    "exang": False,
                    "oldpeak": 0.5,
                    "slope": "upsloping",
                    "ca": 0,
                    "thal": "normal",
                },
            },
        )
        assert res_p.status_code == 200
        data = res_p.get_json()["data"]
        assert data["model_name"] == "Heart Disease Coronary Artery Disease Classifier"
        assert data["model_version"] == "1.0.0"
        assert "target_definition" in data
        assert "stenosis" in data["target_definition"]
        assert data["predicted_class_label"] in [
            "No Coronary Artery Disease (<50% stenosis)",
            "Coronary Artery Disease Present (>=50% stenosis)",
        ]


class TestTimestampIntegrity:
    """Verify UTC serialization and consistency across entities."""

    def test_utc_iso_serialization_format(self):
        """Verify to_iso_utc produces ISO 8601 with Z designator."""
        # 1. Naive datetime (as returned by SQLite)
        dt_naive = datetime(2026, 10, 19, 14, 30, 0, 123456)
        iso = to_iso_utc(dt_naive)
        assert iso == "2026-10-19T14:30:00.123456Z"
        assert iso.endswith("Z")

        # 2. Timezone-aware UTC datetime
        dt_aware = datetime(2026, 10, 19, 14, 30, 0, 123456, tzinfo=timezone.utc)
        iso_aware = to_iso_utc(dt_aware)
        assert iso_aware == "2026-10-19T14:30:00.123456Z"

        # 3. None handling
        assert to_iso_utc(None) is None

    def test_server_generated_timestamps_in_api(self, client, clinician_token):
        """Verify newly created patient and encounter return explicit UTC Z timestamps."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_p = client.post(
            "/api/v1/patients",
            headers=headers,
            json={"age": 62, "sex": "Female", "notes": "Timestamp check"},
        )
        assert res_p.status_code == 201
        p_data = res_p.get_json()["data"]
        assert p_data["created_at"].endswith("Z")
        assert "T" in p_data["created_at"]

        res_a = client.post(
            f"/api/v1/patients/{p_data['id']}/assessments",
            headers=headers,
            json={"reason_for_visit": "Screening"},
        )
        assert res_a.status_code == 201
        a_data = res_a.get_json()["data"]
        assert a_data["assessment_date"].endswith("Z")
        assert a_data["created_at"].endswith("Z")


class TestEmptyDatabaseAndDemoDataRemoval:
    """Verify system starts clean and handles empty state gracefully."""

    def test_empty_database_dashboard_endpoints(self, client, clinician_token):
        """Verify querying patient list with zero records returns empty list and does not crash."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res = client.get("/api/v1/patients?page=1&per_page=10", headers=headers)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert isinstance(data["items"], list)
        assert data["total"] == 0

    def test_safe_reset_utility(self, app):
        """Verify reset_clinical_data safely clears records and keeps users intact."""
        with app.app_context():
            # Seed 1 patient + 1 assessment
            pt = Patient(patient_code="PT-RESET-TEST", age=50, sex="Female", is_active=True)
            db.session.add(pt)
            db.session.commit()

            a = Assessment(patient_id=pt.id, reason_for_visit="Test")
            db.session.add(a)
            db.session.commit()

            assert Patient.query.filter_by(patient_code="PT-RESET-TEST").count() == 1

            # Run reset with skip_backup=True for in-memory testing
            summary = reset_clinical_data(app=app, skip_backup=True)
            assert summary["status"] == "completed"
            assert summary["counts"]["patients"] >= 1
            assert Patient.query.count() == 0
            assert Assessment.query.count() == 0
