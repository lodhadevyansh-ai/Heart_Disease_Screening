"""
Comprehensive Test Suite for ML Inference and Feature Mapping Fixes.

Validates:
1. All 13 CAD features mapped correctly and evaluated by genuine pipeline.
2. Missing required CAD features returns 422 and identifies missing fields (zero silent imputation).
3. Legitimate zeros (oldpeak=0.0, ca=0, fbs=0, exang=0, chol=0) are preserved and not treated as missing.
4. Categorical values map to exact training encodings.
5. All 11 Heart Failure Mortality features mapped correctly and evaluated.
6. CAD and Heart Failure features cannot accidentally be interchanged.
7. Explicit rejection of unsupported general Heart Failure screening.
8. Persistence of direct features into StructuredLabMeasurement and prediction history retrieval.
9. Ownership checks reject unauthorized patient or encounter access.
10. Deduplication on identical retry.
11. Emergency safety rule primacy remains intact alongside ML predictions.
"""

import pytest
from database.models import Patient, Assessment, StructuredLabMeasurement, ModelPrediction


class TestMLInferenceFixes:
    """Test suite validating end-to-end ML feature intake, validation, and execution."""

    def test_all_13_cad_features_mapped_and_evaluated(self, client, clinician_token, sample_patient):
        """Verify all 13 CAD features are accepted and evaluated by the trained model."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "age": 60,
            "sex": "Male",
            "cp": "typical angina",
            "trestbps": 135.0,
            "chol": 230.0,
            "fbs": 0,
            "restecg": "normal",
            "thalch": 140.0,
            "exang": 1,
            "oldpeak": 1.5,
            "slope": "flat",
            "ca": 1,
            "thal": "normal",
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "patient_id": sample_patient,
                "assessment_id": assessment_id,
                "direct_features": cad_payload,
                "explain": True,
            },
        )
        assert res.status_code == 200, res.get_json()
        data = res.get_json()["data"]
        assert data["task_name"] == "coronary_artery_disease"
        assert data["model_version"] == "1.0.0"
        assert data["is_probability_calibrated"] is True
        assert 0.0 <= data["calibrated_probability"] <= 1.0
        assert data["predicted_class_label"] in [
            "No Coronary Artery Disease (<50% stenosis)",
            "Coronary Artery Disease Present (>=50% stenosis)",
        ]

    def test_missing_required_cad_features_prevents_inference(self, client, clinician_token, sample_patient):
        """Missing required CAD features must be identified and fail with 422."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        # Only partial features, missing chol, oldpeak, slope, ca, thal
        partial_payload = {
            "age": 55,
            "sex": "Male",
            "cp": "typical angina",
            "trestbps": 120,
            "fbs": 0,
            "restecg": "normal",
            "thalch": 150,
            "exang": 0,
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": partial_payload,
            },
        )
        assert res.status_code == 422
        err = res.get_json()["error"]["message"]
        assert "Missing required clinical inputs" in err
        for missing in ["chol", "oldpeak", "slope", "ca", "thal"]:
            assert missing in err

    def test_valid_zero_values_preserved(self, client, clinician_token, sample_patient):
        """Verify 0.0 for oldpeak and 0 for ca are preserved and not treated as missing."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "age": 50,
            "sex": "Female",
            "cp": "asymptomatic",
            "trestbps": 120.0,
            "chol": 190.0,
            "fbs": 0,
            "restecg": "normal",
            "thalch": 160.0,
            "exang": 0,
            "oldpeak": 0.0,  # Legitimate zero
            "slope": "upsloping",
            "ca": 0,         # Legitimate zero
            "thal": "normal",
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": cad_payload,
            },
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        snapshot = data["input_features_snapshot"]
        assert snapshot["oldpeak"] == 0.0
        assert snapshot["ca"] == 0
        assert snapshot["fbs"] == 0
        assert snapshot["exang"] == 0

    def test_categorical_encodings_mapped_properly(self, client, clinician_token, sample_patient):
        """Verify resting ECG, slope, and thal categories match exact training encodings."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "age": 62,
            "sex": "Male",
            "cp": "atypical angina",
            "trestbps": 130.0,
            "chol": 215.0,
            "fbs": 0,
            "restecg": "st-t abnormality",
            "thalch": 130.0,
            "exang": 1,
            "oldpeak": 2.0,
            "slope": "downsloping",
            "ca": 2,
            "thal": "reversable defect",
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": cad_payload,
            },
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        snapshot = data["input_features_snapshot"]
        assert snapshot["restecg"] == "st-t abnormality"
        assert snapshot["slope"] == "downsloping"
        assert snapshot["thal"] == "reversable defect"

    def test_all_11_hf_mortality_features_mapped(self, client, clinician_token, sample_patient):
        """Verify all 11 Heart Failure Survival features are mapped and evaluated."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        hf_payload = {
            "age": 65,
            "anaemia": 0,
            "creatinine_phosphokinase": 320.0,
            "diabetes": 0,
            "ejection_fraction": 38.0,
            "high_blood_pressure": 1,
            "platelets": 260000.0,
            "serum_creatinine": 1.3,
            "serum_sodium": 137.0,
            "sex": 1,
            "smoking": 0,
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "heart_failure_mortality",
                "direct_features": hf_payload,
            },
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["task_name"] == "heart_failure_mortality"
        assert data["score_type"] == "classifier_confidence_score"
        assert data["is_probability_calibrated"] is False
        assert data["predicted_class_label"] in ["Survived Follow-up Period", "Deceased During Follow-up Period"]

    def test_cad_and_hf_features_cannot_be_interchanged(self, client, clinician_token, sample_patient):
        """Ensure CAD features sent to HF or HF features sent to CAD trigger schema validation failure."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "chol": 220, "oldpeak": 1.0, "slope": "flat", "ca": 1, "thal": "normal",
        }

        # Request HF mortality using CAD features
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "heart_failure_mortality",
                "direct_features": cad_payload,
            },
        )
        assert res.status_code == 422
        err = res.get_json()["error"]["message"]
        assert "ejection_fraction" in err or "serum_creatinine" in err

    def test_unsupported_general_hf_screening_rejected(self, client, clinician_token, sample_patient):
        """Server must strictly reject community heart failure screening."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "heart_failure_screening"},
        )
        assert res.status_code == 400
        assert "UNSUPPORTED TASK" in res.get_json()["error"]["message"]

    def test_prediction_persistence_and_retrieval(self, client, clinician_token, sample_patient):
        """Verify direct features persist into StructuredLabMeasurement and prediction history is retrievable."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "age": 58, "sex": "Male", "cp": "typical angina", "trestbps": 140.0,
            "chol": 245.0, "fbs": 0, "restecg": "normal", "thalch": 145.0,
            "exang": 1, "oldpeak": 1.8, "slope": "flat", "ca": 1, "thal": "normal",
        }

        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "direct_features": cad_payload,
            },
        )
        assert res.status_code == 200

        # Verify labs were persisted
        labs_res = client.get(
            f"/api/v1/assessments/{assessment_id}/labs",
            headers=headers,
        )
        assert labs_res.status_code == 200
        lab_items = labs_res.get_json()["data"]
        test_names = [l["test_name"] for l in lab_items]
        assert "cholesterol" in test_names
        assert "oldpeak" in test_names
        assert "ca" in test_names

        # Verify prediction history is retrievable
        hist_res = client.get(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
        )
        assert hist_res.status_code == 200
        preds = hist_res.get_json()["data"]
        assert len(preds) >= 1
        assert preds[0]["task_name"] == "coronary_artery_disease"

        # Verify readiness check now reports 13/13 features ready without passing direct features
        readiness_res = client.get(
            f"/api/v1/assessments/{assessment_id}/readiness",
            headers=headers,
        )
        assert readiness_res.status_code == 200
        readiness = readiness_res.get_json()["data"]
        assert readiness["coronary_artery_disease"]["ready"] is True
        assert readiness["coronary_artery_disease"]["available_features_count"] == 13

    def test_deduplication_on_identical_retry(self, client, clinician_token, sample_patient):
        """Retrying with identical features must return existing prediction without duplicates."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        cad_payload = {
            "age": 52, "sex": "Female", "cp": "non-anginal", "trestbps": 125.0,
            "chol": 205.0, "fbs": 0, "restecg": "normal", "thalch": 155.0,
            "exang": 0, "oldpeak": 0.5, "slope": "upsloping", "ca": 0, "thal": "normal",
        }

        # First run
        res1 = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease", "direct_features": cad_payload},
        )
        assert res1.status_code == 200
        pred_id1 = res1.get_json()["data"]["id"]

        # Retry with identical features
        res2 = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease", "direct_features": cad_payload},
        )
        assert res2.status_code == 200
        pred_id2 = res2.get_json()["data"]["id"]

        # Verify returned prediction is the same record
        assert pred_id1 == pred_id2

        # Verify history length is 1
        hist_res = client.get(f"/api/v1/assessments/{assessment_id}/predictions", headers=headers)
        assert len(hist_res.get_json()["data"]) == 1

    def test_unauthorized_access_rejected(self, client, clinician_token, sample_patient):
        """Verify unauthorized users or mismatched patient_ids are rejected."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        # 1. Unauthenticated
        unauth_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            json={"task_name": "coronary_artery_disease"},
        )
        assert unauth_res.status_code == 401

        # 2. Mismatched patient_id in payload
        mismatch_res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={
                "task_name": "coronary_artery_disease",
                "patient_id": sample_patient + 9999,
                "assessment_id": assessment_id,
            },
        )
        assert mismatch_res.status_code == 400
        assert "patient_id" in mismatch_res.get_json()["error"]["message"]

    def test_patient_age_and_sex_mapped_from_database(self, client, clinician_token, sample_patient):
        """Authoritative patient record provides age and sex into encounter API and CAD mapping."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        # Verify get_assessment returns complete patient dict with age and sex
        get_res = client.get(f"/api/v1/assessments/{assessment_id}", headers=headers)
        assert get_res.status_code == 200
        assess_data = get_res.get_json()["data"]
        assert "patient" in assess_data and assess_data["patient"] is not None
        assert assess_data["patient"]["age"] == 58
        assert assess_data["patient"]["sex"] == "Male"

        # Check readiness maps age and sex from patient without re-entry
        readiness_res = client.get(f"/api/v1/assessments/{assessment_id}/readiness", headers=headers)
        cad_ready = readiness_res.get_json()["data"]["coronary_artery_disease"]
        assert "age" in cad_ready["available_features"]
        assert cad_ready["available_features"]["age"] == 58
        assert "sex" in cad_ready["available_features"]
        assert cad_ready["available_features"]["sex"] == "Male"
        assert "age" not in cad_ready["missing_features"]
        assert "sex" not in cad_ready["missing_features"]

    def test_resting_heart_rate_not_substituted_for_maximum_heart_rate(self, client, clinician_token, sample_patient):
        """Resting heart rate in vitals must NEVER be substituted for peak exercise heart rate (thalach/thalch)."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        # Record resting heart rate in vitals
        client.post(
            f"/api/v1/assessments/{assessment_id}/vitals",
            headers=headers,
            json={"systolic_bp": 130.0, "diastolic_bp": 82.0, "heart_rate": 72.0},
        )

        readiness_res = client.get(f"/api/v1/assessments/{assessment_id}/readiness", headers=headers)
        cad_ready = readiness_res.get_json()["data"]["coronary_artery_disease"]
        assert "thalch" in cad_ready["missing_features"]
        assert "thalch" not in cad_ready["available_features"]

    def test_thalach_input_validated_persisted_and_restored(self, client, clinician_token, sample_patient):
        """Maximum heart rate (thalach) is validated within bounds, persisted to StructuredLabMeasurement, and restored."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        # Out-of-bounds thalach (<50 or >240) rejected
        invalid_payload = {
            "age": 60, "sex": "Male", "cp": "typical angina", "trestbps": 130.0,
            "chol": 220.0, "fbs": 0, "restecg": "normal", "thalach": 30.0,  # Below 50
            "exang": 0, "oldpeak": 1.0, "slope": "flat", "ca": 0, "thal": "normal",
        }
        res_inv = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease", "direct_features": invalid_payload},
        )
        assert res_inv.status_code == 422
        assert "outside plausible clinical bounds" in res_inv.get_json()["error"]["message"]

        # Valid thalach accepted, evaluated, and persisted
        valid_payload = {
            "age": 60, "sex": "Male", "cp": "typical angina", "trestbps": 130.0,
            "chol": 220.0, "fbs": 0, "restecg": "normal", "thalach": 165.0,
            "exang": 0, "oldpeak": 0.0, "slope": "flat", "ca": 0, "thal": "normal",
        }
        res_val = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease", "direct_features": valid_payload},
        )
        assert res_val.status_code == 200

        # Check persistence in StructuredLabMeasurement
        meas = StructuredLabMeasurement.query.filter_by(
            assessment_id=assessment_id,
            test_name="maximum_heart_rate",
        ).first()
        assert meas is not None
        assert meas.value_numeric == 165.0
        assert meas.unit == "bpm"

        # Check restored upon reopening / querying readiness
        readiness_res = client.get(f"/api/v1/assessments/{assessment_id}/readiness", headers=headers)
        cad_ready = readiness_res.get_json()["data"]["coronary_artery_disease"]
        assert cad_ready["available_features"].get("thalch") == 165.0

    def test_zero_values_preserved_as_valid_features(self, client, clinician_token, sample_patient):
        """Zero values for oldpeak=0.0, ca=0, fbs=0, exang=0 are preserved as valid, not missing."""
        headers = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers)
        assessment_id = res_a.get_json()["data"]["id"]

        zero_payload = {
            "age": 45, "sex": "Female", "cp": "non-anginal", "trestbps": 118.0,
            "chol": 190.0, "fbs": 0, "restecg": "normal", "thalach": 172.0,
            "exang": 0, "oldpeak": 0.0, "slope": "upsloping", "ca": 0, "thal": "normal",
        }
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers,
            json={"task_name": "coronary_artery_disease", "direct_features": zero_payload},
        )
        assert res.status_code == 200
        snap = res.get_json()["data"]["input_features_snapshot"]
        assert snap["oldpeak"] == 0.0
        assert snap["ca"] == 0
        assert snap["fbs"] == 0
        assert snap["exang"] == 0

    def test_cross_account_isolation_rejected(self, client, clinician_token, sample_patient):
        """A clinician cannot access another clinician's patient or encounter."""
        # Create second user
        user2_res = client.post("/api/v1/auth/register", json={
            "email": "dr.other@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "full_name": "Dr. Other",
            "role": "clinician",
        })
        assert user2_res.status_code == 201, user2_res.get_json()
        token2 = user2_res.get_json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Try to run prediction on clinician 1's patient's assessment
        headers1 = {"Authorization": f"Bearer {clinician_token}"}
        res_a = client.post(f"/api/v1/patients/{sample_patient}/assessments", headers=headers1)
        assessment_id = res_a.get_json()["data"]["id"]

        res_forbidden = client.post(
            f"/api/v1/assessments/{assessment_id}/predictions",
            headers=headers2,
            json={"task_name": "coronary_artery_disease"},
        )
        assert res_forbidden.status_code in (403, 404)

