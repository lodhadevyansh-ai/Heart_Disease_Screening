"""
Tests for Phase 7: Shared ML Inference Interface.

Validates:
1. Predictor loading of supported trained models.
2. Input schema validation, missing field detection (no silent imputation),
   categorical validation, and numeric bound checks.
3. Explicit rejection of unsupported clinical tasks (heart failure screening,
   arrhythmia symptom screening).
4. Deterministic inference reproducibility.
5. Distinction between classifier scores and calibrated probabilities.
6. Local explainability attributions with mandatory non-causal guardrails.
7. Calibration metrics (Brier score, ECE, reliability curves).
8. Isolation of model tasks (no combining separate scores).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_Learning.src.predict import (
    predict_clinical_condition,
    validate_input_features,
    load_model_and_metadata,
    UnsupportedTaskError,
    ValidationError,
    ModelArtifactNotFoundError,
    SUPPORTED_TASKS,
    UNSUPPORTED_TASKS,
)
from Machine_Learning.src.calibration import (
    compute_expected_calibration_error,
    compute_calibration_diagnostics,
    fit_calibrated_pipeline,
)
from Machine_Learning.src.explainability import (
    explain_prediction_local,
    compute_cohort_feature_importance,
    CAUSAL_DISCLAIMER,
)


# Synthetic valid test fixtures
@pytest.fixture
def valid_cad_input():
    return {
        "age": 58,
        "sex": "Male",
        "cp": "typical angina",
        "trestbps": 140.0,
        "chol": 240.0,
        "fbs": False,
        "restecg": "normal",
        "thalch": 145.0,
        "exang": True,
        "oldpeak": 2.2,
        "slope": "flat",
        "ca": 1,
        "thal": "reversable defect",
    }


@pytest.fixture
def valid_hf_mortality_input():
    return {
        "age": 65,
        "anaemia": 0,
        "creatinine_phosphokinase": 250.0,
        "diabetes": 0,
        "ejection_fraction": 35.0,
        "high_blood_pressure": 1,
        "platelets": 263358.0,
        "serum_creatinine": 1.4,
        "serum_sodium": 136.0,
        "sex": 1,
        "smoking": 0,
    }


@pytest.fixture
def valid_ecg_arrhythmia_input():
    # 279 numerical precomputed 12-lead features
    row = {str(i): 0.0 for i in range(279)}
    row["0"] = 62.0   # Age
    row["1"] = 1.0    # Sex
    row["2"] = 172.0  # Height
    row["3"] = 75.0   # Weight
    row["4"] = 88.0   # QRS duration
    row["5"] = 155.0  # P-R interval
    row["6"] = 390.0  # Q-T interval
    row["14"] = 70.0  # Heart rate
    return row


class TestSharedInferenceEngine:
    """Test suite for shared prediction interface and schema validation."""

    def test_successful_cad_prediction(self, valid_cad_input):
        result = predict_clinical_condition("coronary_artery_disease", valid_cad_input)
        assert result["status"] == "success"
        assert result["task"] == "coronary_artery_disease"
        assert "predicted_class_id" in result["prediction"]
        assert result["prediction"]["predicted_class_id"] in [0, 1]
        assert result["prediction"]["is_probability_calibrated"] is True
        assert result["prediction"]["score_type"] == "calibrated_probability"
        assert 0.0 <= result["prediction"]["score"] <= 1.0
        assert "clinical_prototype_disclaimer" in result

    def test_deterministic_inference(self, valid_cad_input):
        res1 = predict_clinical_condition("coronary_artery_disease", valid_cad_input)
        res2 = predict_clinical_condition("coronary_artery_disease", valid_cad_input)
        assert res1["prediction"]["predicted_class_id"] == res2["prediction"]["predicted_class_id"]
        assert res1["prediction"]["score"] == res2["prediction"]["score"]
        assert res1["prediction"]["class_probabilities"] == res2["prediction"]["class_probabilities"]

    def test_missing_required_features_rejected(self, valid_cad_input):
        incomplete = valid_cad_input.copy()
        del incomplete["cp"]
        del incomplete["oldpeak"]

        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("coronary_artery_disease", incomplete)
        
        err_msg = str(exc_info.value)
        assert "Missing required clinical inputs" in err_msg
        assert "cp" in err_msg
        assert "oldpeak" in err_msg

    def test_null_value_rejected_no_silent_imputation(self, valid_cad_input):
        null_input = valid_cad_input.copy()
        null_input["chol"] = None

        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("coronary_artery_disease", null_input)
        assert "null/empty" in str(exc_info.value)

    def test_out_of_bounds_numeric_rejected(self, valid_cad_input):
        # Implausible age
        invalid_age = valid_cad_input.copy()
        invalid_age["age"] = 160
        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("coronary_artery_disease", invalid_age)
        assert "outside plausible clinical bounds" in str(exc_info.value)

        # Implausible blood pressure
        invalid_bp = valid_cad_input.copy()
        invalid_bp["trestbps"] = 15.0
        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("coronary_artery_disease", invalid_bp)
        assert "outside plausible clinical bounds" in str(exc_info.value)

    def test_invalid_categorical_value_rejected(self, valid_cad_input):
        invalid_cp = valid_cad_input.copy()
        invalid_cp["cp"] = "atypical migraine"
        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("coronary_artery_disease", invalid_cp)
        assert "invalid value" in str(exc_info.value)

    def test_unsupported_heart_failure_screening_rejected(self, valid_hf_mortality_input):
        # Specifically requesting screening or diagnosis on HF dataset must fail
        with pytest.raises(UnsupportedTaskError) as exc_info:
            predict_clinical_condition("heart_failure_screening", valid_hf_mortality_input)
        assert "UNSUPPORTED TASK" in str(exc_info.value)
        assert "heart_failure.csv" in str(exc_info.value)

        with pytest.raises(UnsupportedTaskError) as exc_info2:
            predict_clinical_condition("heart_failure_diagnosis", valid_hf_mortality_input)
        assert "UNSUPPORTED TASK" in str(exc_info2.value)

    def test_supported_heart_failure_mortality_prediction(self, valid_hf_mortality_input):
        result = predict_clinical_condition("heart_failure_mortality", valid_hf_mortality_input)
        assert result["status"] == "success"
        assert result["prediction"]["predicted_class_id"] in [0, 1]
        assert result["prediction"]["is_probability_calibrated"] is False
        assert result["prediction"]["score_type"] == "classifier_confidence_score"
        assert 0.0 <= result["prediction"]["score"] <= 1.0

    def test_unsupported_arrhythmia_symptom_screening_rejected(self):
        symptom_payload = {"palpitations": 1, "dizziness": 1, "age": 45}
        with pytest.raises(UnsupportedTaskError) as exc_info:
            predict_clinical_condition("arrhythmia_symptom_screening", symptom_payload)
        assert "UNSUPPORTED TASK" in str(exc_info.value)
        assert "279 precomputed" in str(exc_info.value)

    def test_arrhythmia_insufficient_features_rejected(self):
        few_features = {str(i): 1.0 for i in range(10)}
        with pytest.raises(ValidationError) as exc_info:
            predict_clinical_condition("arrhythmia_ecg", few_features)
        assert "requires at least 279" in str(exc_info.value)

    def test_supported_arrhythmia_ecg_prediction(self, valid_ecg_arrhythmia_input):
        result = predict_clinical_condition("arrhythmia_ecg", valid_ecg_arrhythmia_input)
        assert result["status"] == "success"
        assert result["prediction"]["predicted_class_id"] in [0, 1, 2, 3, 4]
        assert "class_probabilities" in result["prediction"]
        assert len(result["prediction"]["class_probabilities"]) == 5

    def test_models_not_combined_into_aggregate(self, valid_cad_input, valid_hf_mortality_input):
        # CAD inference
        cad_res = predict_clinical_condition("coronary_artery_disease", valid_cad_input)
        # HF mortality inference
        hf_res = predict_clinical_condition("heart_failure_mortality", valid_hf_mortality_input)

        # Verify strict isolation
        assert cad_res["task"] != hf_res["task"]
        assert "aggregate_risk" not in cad_res["prediction"]
        assert "aggregate_risk" not in hf_res["prediction"]
        assert cad_res["task_scope"]["target_definition"] != hf_res["task_scope"]["target_definition"]


class TestExplainabilityAndGuardrails:
    """Test suite for feature attribution and non-causal guardrails."""

    def test_cad_local_explanation_contains_disclaimer(self, valid_cad_input):
        result = predict_clinical_condition("coronary_artery_disease", valid_cad_input, explain=True)
        assert "explanation" in result
        exp = result["explanation"]
        assert exp["status"] == "success"
        assert "non_causal_disclaimer" in exp
        assert exp["non_causal_disclaimer"] == CAUSAL_DISCLAIMER
        assert "DO NOT represent causal mechanisms" in exp["non_causal_disclaimer"]
        assert len(exp["all_attributions"]) > 0

    def test_hf_tree_explanation(self, valid_hf_mortality_input):
        result = predict_clinical_condition("heart_failure_mortality", valid_hf_mortality_input, explain=True)
        assert "explanation" in result
        exp = result["explanation"]
        assert exp["status"] == "success"
        assert "top_risk_increasing_features" in exp
        assert "top_risk_decreasing_features" in exp
        assert exp["non_causal_disclaimer"] == CAUSAL_DISCLAIMER


class TestProbabilityCalibration:
    """Test suite for calibration metrics and ECE calculation."""

    def test_expected_calibration_error_perfect_calibration(self):
        # When probabilities match empirical frequencies exactly
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.0, 0.0, 1.0, 1.0])
        ece = compute_expected_calibration_error(y_true, y_prob, n_bins=2)
        assert np.isclose(ece, 0.0)

    def test_expected_calibration_error_miscalibrated(self):
        # Extreme overconfidence: all 1s predicted with 1.0 prob, but labels are all 0
        y_true = np.zeros(100, dtype=int)
        y_prob = np.ones(100, dtype=float)
        ece = compute_expected_calibration_error(y_true, y_prob, n_bins=5)
        assert np.isclose(ece, 1.0)

    def test_calibration_diagnostics(self):
        np.random.seed(42)
        y_true = np.random.binomial(1, 0.5, size=100)
        y_prob = np.random.uniform(0.1, 0.9, size=100)
        diag = compute_calibration_diagnostics(y_true, y_prob, n_bins=5)

        assert "brier_score" in diag
        assert "expected_calibration_error" in diag
        assert "calibration_quality" in diag
        assert "reliability_curve" in diag
        assert 0.0 <= diag["brier_score"] <= 1.0
        assert 0.0 <= diag["expected_calibration_error"] <= 1.0
