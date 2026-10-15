"""Unit and pipeline tests for Machine Learning modules.

Covers data loaders, schema validation, feature engineering,
preprocessing pipelines, data leakage prevention, and inference robustness.
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

from Machine_Learning.src.data_loader import (
    load_heart_disease_data,
    load_heart_failure_data,
    load_arrhythmia_data,
    load_dataset,
    audit_dataframe,
    audit_all_datasets,
    DatasetNotFoundError,
    DatasetValidationError,
    HEART_DISEASE_UCI_COLUMNS,
    HEART_FAILURE_COLUMNS,
)
from Machine_Learning.src.feature_engineering import (
    HeartDiseaseFeatureEngineer,
    HeartFailureFeatureEngineer,
    ArrhythmiaFeatureEngineer,
)
from Machine_Learning.src.preprocessing import (
    build_heart_disease_preprocessor,
    build_heart_failure_preprocessor,
    build_arrhythmia_preprocessor,
    prepare_heart_disease_splits,
    prepare_heart_failure_splits,
    prepare_arrhythmia_splits,
    preprocess_inference_input,
    HEART_DISEASE_RAW_FEATURES,
    HEART_FAILURE_RAW_FEATURES,
    DatasetSplits,
)


class TestDataLoaders:
    """Test suite for dataset loaders."""

    def test_load_heart_disease_uci(self):
        df = load_heart_disease_data()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (920, 16)
        assert list(df.columns) == HEART_DISEASE_UCI_COLUMNS
        assert df["num"].nunique() == 5
        assert set(df["sex"].unique()) == {"Male", "Female"}

    def test_load_heart_failure(self):
        df = load_heart_failure_data()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (299, 13)
        assert list(df.columns) == HEART_FAILURE_COLUMNS
        assert set(df["DEATH_EVENT"].unique()) == {0, 1}
        assert df.isnull().sum().sum() == 0

    def test_load_arrhythmia(self):
        df = load_arrhythmia_data()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (430, 280)
        assert "condition_group" in df.columns
        assert set(df["condition_group"].unique()) == {
            "Normal",
            "Ischemic_MI_Related",
            "Conduction_Abnormality",
            "Rhythm_Abnormality",
            "Structural_Atrial_Abnormality",
        }

    def test_load_dataset_dispatcher(self):
        df1 = load_dataset("heart_disease_uci")
        assert df1.shape == (920, 16)

        df2 = load_dataset("heart_failure")
        assert df2.shape == (299, 13)

        df3 = load_dataset("arrhythmia_conditions")
        assert df3.shape == (430, 280)

        with pytest.raises(ValueError, match="Unknown dataset name"):
            load_dataset("unknown_dataset_xyz")

    def test_missing_file_raises_not_found_error(self):
        with pytest.raises(DatasetNotFoundError):
            load_heart_disease_data("non_existent_file.csv")

    def test_raw_data_immutability(self):
        df1 = load_heart_disease_data()
        original_shape = df1.shape
        # Mutate the dataframe in memory
        df1["new_mutated_col"] = 999
        df1.drop(columns=["age"], inplace=True)

        # Reload should be unaffected
        df2 = load_heart_disease_data()
        assert df2.shape == original_shape
        assert "age" in df2.columns
        assert "new_mutated_col" not in df2.columns

    def test_audit_all_datasets(self):
        reports = audit_all_datasets()
        assert "heart_disease_uci" in reports
        assert "heart_failure" in reports
        assert "arrhythmia_conditions" in reports

        hd_rep = reports["heart_disease_uci"]
        assert hd_rep.row_count == 920
        assert hd_rep.duplicate_rows == 0
        assert "chol" in hd_rep.missing_values or any("chol" in a for a in hd_rep.anomalies)

        hf_rep = reports["heart_failure"]
        assert hf_rep.row_count == 299
        assert hf_rep.target_column == "DEATH_EVENT"
        assert any("DEATH_EVENT" in a for a in hf_rep.anomalies)
        assert any("time" in a for a in hf_rep.anomalies)

        arr_rep = reports["arrhythmia_conditions"]
        assert arr_rep.row_count == 430
        assert arr_rep.target_column == "condition_group"
        assert "13" in arr_rep.missing_values


class TestFeatureEngineering:
    """Test suite for clinical feature engineering transformers."""

    def test_heart_disease_feature_engineer(self):
        sample_df = pd.DataFrame({
            "age": [50, 70],
            "thalch": [170, 110],
            "oldpeak": [0.5, 2.0]
        })
        fe = HeartDiseaseFeatureEngineer()
        out = fe.fit_transform(sample_df)

        assert "max_hr_ratio" in out.columns
        assert "chronotropic_incompetence" in out.columns
        assert "st_depression_significant" in out.columns
        assert "age_ge_60" in out.columns

        # Patient 1 (age 50, thalch 170): 170 / (220 - 50) = 1.0 (no chronotropic incompetence)
        assert out.loc[0, "chronotropic_incompetence"] == 0.0
        assert out.loc[0, "age_ge_60"] == 0.0
        assert out.loc[0, "st_depression_significant"] == 0.0

        # Patient 2 (age 70, thalch 110): 110 / 150 = 0.733 (<0.85 -> chronotropic incompetence)
        assert out.loc[1, "chronotropic_incompetence"] == 1.0
        assert out.loc[1, "age_ge_60"] == 1.0
        assert out.loc[1, "st_depression_significant"] == 1.0

    def test_heart_failure_feature_engineer(self):
        sample_df = pd.DataFrame({
            "age": [50, 72],
            "ejection_fraction": [55, 25],
            "serum_creatinine": [1.0, 2.2],
            "high_blood_pressure": [0, 1]
        })
        fe = HeartFailureFeatureEngineer()
        out = fe.fit_transform(sample_df)

        assert "reduced_ef" in out.columns
        assert "severe_ef_reduction" in out.columns
        assert "renal_dysfunction" in out.columns
        assert "cardiorenal_risk" in out.columns
        assert "hypertension_elderly" in out.columns

        assert out.loc[0, "reduced_ef"] == 0.0
        assert out.loc[0, "renal_dysfunction"] == 0.0
        assert out.loc[1, "reduced_ef"] == 1.0
        assert out.loc[1, "severe_ef_reduction"] == 1.0
        assert out.loc[1, "renal_dysfunction"] == 1.0
        assert out.loc[1, "cardiorenal_risk"] == 1.0
        assert out.loc[1, "hypertension_elderly"] == 1.0

    def test_arrhythmia_feature_engineer(self):
        sample_df = pd.DataFrame({
            "2": [165.0, 780.0],  # Outlier height
            "4": [80.0, 140.0],   # QRS duration
            "5": [160.0, 220.0],  # PR interval
            "6": [380.0, 480.0],  # QT interval
            "14": [75.0, 110.0]   # Heart rate
        })
        fe = ArrhythmiaFeatureEngineer()
        out = fe.fit_transform(sample_df)

        # Height outlier > 250 cm should be converted to NaN
        assert np.isnan(out.loc[1, "2"])
        assert out.loc[0, "2"] == 165.0

        # Conduction flags
        assert "qrs_wide" in out.columns
        assert "pr_prolonged" in out.columns
        assert "qtc_bazett" in out.columns
        assert "tachycardia" in out.columns

        assert out.loc[0, "qrs_wide"] == 0.0
        assert out.loc[1, "qrs_wide"] == 1.0  # QRS 140 > 120
        assert out.loc[1, "pr_prolonged"] == 1.0  # PR 220 > 200
        assert out.loc[1, "tachycardia"] == 1.0  # HR 110 > 100


class TestPreprocessingPipelines:
    """Test suite for preprocessing pipelines, train/test splits, and leakage prevention."""

    def test_heart_disease_splits_and_leakage_control(self):
        df = load_heart_disease_data()
        splits = prepare_heart_disease_splits(df, test_size=0.2, val_size=0.1, random_state=42)

        assert isinstance(splits, DatasetSplits)
        # Check shapes: 920 total -> train ~ 644 (70%), val ~ 92 (10%), test ~ 184 (20%)
        assert splits.X_train.shape[0] == 644
        assert splits.X_val.shape[0] == 92
        assert splits.X_test.shape[0] == 184
        assert splits.X_train.shape[1] == splits.X_test.shape[1]

        # No NaNs in transformed output arrays
        assert not np.isnan(splits.X_train).any()
        assert not np.isnan(splits.X_val).any()
        assert not np.isnan(splits.X_test).any()

        # Target stratification check (approx 55% CAD positive)
        pos_train_rate = np.mean(splits.y_train)
        pos_test_rate = np.mean(splits.y_test)
        assert abs(pos_train_rate - pos_test_rate) < 0.02

    def test_heart_failure_splits_drops_time_leakage(self):
        df = load_heart_failure_data()
        assert "time" in df.columns

        splits = prepare_heart_failure_splits(df, test_size=0.2, val_size=0.1, random_state=42)
        assert isinstance(splits, DatasetSplits)

        # Confirm 299 total -> 209 train (70%), 30 val (10%), 60 test (20%)
        assert splits.X_train.shape[0] == 209
        assert splits.X_val.shape[0] == 30
        assert splits.X_test.shape[0] == 60

        # Confirm 'time' is NOT in feature names
        assert "time" not in splits.feature_names_out
        assert not np.isnan(splits.X_train).any()
        assert not np.isnan(splits.X_test).any()

        # Stratification on DEATH_EVENT (~32% mortality)
        assert abs(np.mean(splits.y_train) - np.mean(splits.y_test)) < 0.05

    def test_arrhythmia_splits_and_stratification(self):
        df = load_arrhythmia_data()
        splits = prepare_arrhythmia_splits(df, test_size=0.2, val_size=0.1, random_state=42)

        assert isinstance(splits, DatasetSplits)
        assert splits.X_train.shape[0] == 301
        assert splits.X_val.shape[0] == 43
        assert splits.X_test.shape[0] == 86

        # Feature 13 (83.3% missing) must be dropped
        assert "13" not in splits.feature_names_out
        # No NaNs remaining after median imputation
        assert not np.isnan(splits.X_train).any()
        assert not np.isnan(splits.X_test).any()

        # Class counts: even the smallest class (9 instances) is preserved across splits
        classes_train = set(np.unique(splits.y_train))
        classes_test = set(np.unique(splits.y_test))
        assert len(classes_train) == 5
        assert len(classes_test) == 5


class TestInferenceConsistencyAndRobustness:
    """Test suite for inference consistency, unexpected categories, missing values, and data types."""

    def test_heart_disease_inference_with_unseen_category(self):
        df = load_heart_disease_data()
        splits = prepare_heart_disease_splits(df, random_state=42)
        preprocessor = splits.preprocessor

        # Sample input with an unseen category in 'cp' and 'restecg'
        sample_input = {
            "age": 55,
            "sex": "Male",
            "cp": "completely_unknown_angina_type",
            "trestbps": 130,
            "chol": 220,
            "fbs": False,
            "restecg": "unknown_ecg_pattern",
            "thalch": 150,
            "exang": False,
            "oldpeak": 1.2,
            "slope": "flat",
            "ca": 0.0,
            "thal": "normal"
        }

        # Should transform smoothly without error; OneHotEncoder ignores unseen categories
        transformed = preprocess_inference_input(
            sample_input, preprocessor, HEART_DISEASE_RAW_FEATURES
        )
        assert isinstance(transformed, np.ndarray)
        assert transformed.shape == (1, splits.X_train.shape[1])
        assert not np.isnan(transformed).any()

    def test_heart_disease_inference_with_missing_columns(self):
        df = load_heart_disease_data()
        splits = prepare_heart_disease_splits(df, random_state=42)
        preprocessor = splits.preprocessor

        # Incomplete patient intake: only age, sex, and chest pain provided
        minimal_input = {
            "age": 62,
            "sex": "Female",
            "cp": "typical angina",
        }

        # Missing columns (chol, trestbps, thalch, ca, etc.) should be filled with NaN and median-imputed
        transformed = preprocess_inference_input(
            minimal_input, preprocessor, HEART_DISEASE_RAW_FEATURES
        )
        assert isinstance(transformed, np.ndarray)
        assert transformed.shape == (1, splits.X_train.shape[1])
        assert not np.isnan(transformed).any()

    def test_inference_reproducibility(self):
        df = load_heart_disease_data()
        splits = prepare_heart_disease_splits(df, random_state=42)

        sample_input = {
            "age": 58, "sex": "Male", "cp": "asymptomatic", "trestbps": 140,
            "chol": 260, "fbs": True, "restecg": "normal", "thalch": 135,
            "exang": True, "oldpeak": 2.5, "slope": "flat", "ca": 1.0, "thal": "reversable defect"
        }

        run_1 = preprocess_inference_input(sample_input, splits.preprocessor, HEART_DISEASE_RAW_FEATURES)
        run_2 = preprocess_inference_input(sample_input, splits.preprocessor, HEART_DISEASE_RAW_FEATURES)

        # Exact numerical reproducibility
        np.testing.assert_array_equal(run_1, run_2)


class TestModelEvaluationAndPersistence:
    """Test suite for evaluation functions, saved artifacts, and metadata integrity."""

    def test_evaluate_binary_classifier_logic(self):
        from Machine_Learning.src.evaluate import evaluate_binary_classifier

        y_true = [0, 0, 1, 1]
        y_pred = [0, 1, 0, 1]
        y_prob = [0.1, 0.7, 0.4, 0.9]

        res = evaluate_binary_classifier(y_true, y_pred, y_prob)

        # TN=1, FP=1, FN=1, TP=1 -> acc=0.5, recall=0.5, precision=0.5, spec=0.5
        assert res["accuracy"] == 0.5
        assert res["recall_sensitivity"] == 0.5
        assert res["precision"] == 0.5
        assert res["specificity"] == 0.5
        assert res["confusion_matrix"]["true_negatives"] == 1
        assert res["confusion_matrix"]["true_positives"] == 1
        assert res["roc_auc"] is not None

    def test_trained_heart_disease_artifact_loads_and_predicts(self):
        import joblib

        artifact_path = PROJECT_ROOT / "Machine_Learning" / "artifacts" / "heart_disease_pipeline_v1.joblib"
        assert artifact_path.exists(), "Trained model artifact heart_disease_pipeline_v1.joblib must exist"

        pipeline = joblib.load(artifact_path)

        sample_patient = pd.DataFrame([{
            "age": 55, "sex": "Male", "cp": "typical angina", "trestbps": 140.0,
            "chol": 240.0, "fbs": False, "restecg": "normal", "thalch": 160.0,
            "exang": False, "oldpeak": 0.8, "slope": "upsloping", "ca": 0.0, "thal": "normal"
        }])

        pred = pipeline.predict(sample_patient)
        proba = pipeline.predict_proba(sample_patient)

        assert pred[0] in [0, 1]
        assert proba.shape == (1, 2)
        assert np.isclose(np.sum(proba), 1.0)
        assert 0.0 <= proba[0, 1] <= 1.0

    def test_heart_disease_metadata_integrity(self):
        import json

        meta_path = PROJECT_ROOT / "Machine_Learning" / "model_metadata" / "heart_disease.json"
        assert meta_path.exists(), "heart_disease.json metadata must exist"

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["dataset"]["name"] == "UCI Heart Disease"
        assert meta["dataset"]["target_column"] == "num"
        assert "measured_test_metrics" in meta
        test_m = meta["measured_test_metrics"]
        assert test_m["roc_auc"] > 0.80
        assert test_m["accuracy"] > 0.75
        assert test_m["sample_count"] == 184
        assert "clinical_prototype_disclaimer" in meta

    def test_heart_failure_artifact_and_task_unsupported_checks(self):
        import joblib
        import json

        # 1. Verify artifact exists and runs on patient features (without 'time')
        artifact_path = PROJECT_ROOT / "Machine_Learning" / "artifacts" / "heart_failure_pipeline_v1.joblib"
        assert artifact_path.exists(), "Trained model artifact heart_failure_pipeline_v1.joblib must exist"

        pipeline = joblib.load(artifact_path)

        sample_hf_patient = pd.DataFrame([{
            "age": 65.0,
            "anaemia": 1,
            "creatinine_phosphokinase": 250,
            "diabetes": 0,
            "ejection_fraction": 30,
            "high_blood_pressure": 1,
            "platelets": 250000.0,
            "serum_creatinine": 1.8,
            "serum_sodium": 135,
            "sex": 1,
            "smoking": 0,
        }])

        pred = pipeline.predict(sample_hf_patient)
        proba = pipeline.predict_proba(sample_hf_patient)

        assert pred[0] in [0, 1]
        assert proba.shape == (1, 2)
        assert np.isclose(np.sum(proba), 1.0)
        assert 0.0 <= proba[0, 1] <= 1.0

        # 2. Verify metadata explicitly documents task mismatch and unsupported status
        meta_path = PROJECT_ROOT / "Machine_Learning" / "model_metadata" / "heart_failure.json"
        assert meta_path.exists(), "heart_failure.json metadata must exist"

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["dataset"]["target_column"] == "DEATH_EVENT"
        feasibility = meta["task_feasibility_and_scope"]
        assert "heart_failure_diagnosis" in feasibility["unsupported_tasks"]
        assert "heart_failure_screening" in feasibility["unsupported_tasks"]
        assert "time" in meta["feature_schema"]["excluded_features"]

        test_m = meta["measured_test_metrics"]
        assert test_m["sample_count"] == 60
        assert test_m["accuracy"] >= 0.65
        assert test_m["specificity"] >= 0.70
        assert "clinical_prototype_disclaimer" in meta

    def test_evaluate_multiclass_classifier_logic(self):
        from Machine_Learning.src.evaluate import evaluate_multiclass_classifier

        y_true = ["Normal", "Normal", "Ischemia", "Arrhythmia"]
        y_pred = ["Normal", "Ischemia", "Ischemia", "Arrhythmia"]
        labels = ["Arrhythmia", "Ischemia", "Normal"]

        res = evaluate_multiclass_classifier(y_true, y_pred, class_labels=labels)

        assert res["sample_count"] == 4
        assert res["class_count"] == 3
        assert res["accuracy"] == 0.75
        assert "per_class_metrics" in res
        assert "Normal" in res["per_class_metrics"]
        assert res["per_class_metrics"]["Normal"]["recall"] == 0.5
        assert res["per_class_metrics"]["Ischemia"]["recall"] == 1.0
        assert res["per_class_metrics"]["Arrhythmia"]["recall"] == 1.0

    def test_arrhythmia_artifact_and_task_unsupported_checks(self):
        import joblib
        import json

        # 1. Verify artifact exists and runs on 12-lead ECG feature vector
        artifact_path = PROJECT_ROOT / "Machine_Learning" / "artifacts" / "arrhythmia_pipeline_v1.joblib"
        assert artifact_path.exists(), "Trained model artifact arrhythmia_pipeline_v1.joblib must exist"

        pipeline = joblib.load(artifact_path)

        # Sample ECG record (columns 0 to 278)
        raw_row = {str(i): 0.0 for i in range(279)}
        raw_row["0"] = 65.0   # Age
        raw_row["1"] = 1.0    # Sex
        raw_row["2"] = 170.0  # Height
        raw_row["3"] = 70.0   # Weight
        raw_row["4"] = 90.0   # QRS
        raw_row["5"] = 160.0  # PR
        raw_row["6"] = 380.0  # QT
        raw_row["14"] = 72.0  # HR
        sample_ecg_df = pd.DataFrame([raw_row])

        pred = pipeline.predict(sample_ecg_df)
        proba = pipeline.predict_proba(sample_ecg_df)

        assert pred[0] in [
            "Normal",
            "Ischemic_MI_Related",
            "Conduction_Abnormality",
            "Rhythm_Abnormality",
            "Structural_Atrial_Abnormality",
        ]
        assert proba.shape == (1, 5)
        assert np.isclose(np.sum(proba), 1.0)
        assert (proba >= 0.0).all() and (proba <= 1.0).all()

        # 2. Verify metadata documents input modality and unsupported tasks
        meta_path = PROJECT_ROOT / "Machine_Learning" / "model_metadata" / "arrhythmia.json"
        assert meta_path.exists(), "arrhythmia.json metadata must exist"

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["dataset"]["target_column"] == "condition_group"
        feasibility = meta["task_feasibility_and_scope"]
        assert "symptom_based_arrhythmia_screening" in feasibility["unsupported_tasks"]
        assert "raw_ecg_signal_interpretation" in feasibility["unsupported_tasks"]
        assert "image_ecg_report_parsing" in feasibility["unsupported_tasks"]
        assert "13" in meta["feature_schema"]["excluded_features"]

        test_m = meta["measured_test_metrics"]
        assert test_m["sample_count"] == 86
        assert test_m["class_count"] == 5
        assert test_m["accuracy"] >= 0.60
        assert "clinical_prototype_disclaimer" in meta


