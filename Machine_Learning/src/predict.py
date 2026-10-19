"""
Shared ML Inference Interface.

Provides a unified, clinical-grade inference engine for supported prediction tasks.
Enforces strict input schema validation, missing-value guards, clear separation
between classifier confidence and calibrated probabilities, explicit unsupported
task rejection, and local explainability with non-causal clinical guardrails.

CLINICAL SAFETY MANDATES:
1. NEVER silently impute missing clinical intake fields with arbitrary defaults.
2. NEVER combine separate model scores into an aggregate "heart disease risk".
3. NEVER return diagnostic predictions for unsupported tasks (e.g. screening
   unselected patients for heart failure using mortality datasets).
4. Do NOT retrain models automatically on application startup.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import joblib
import numpy as np
import pandas as pd

from Machine_Learning.src.explainability import explain_prediction_local, CAUSAL_DISCLAIMER
from Machine_Learning.src.calibration import compute_calibration_diagnostics

# Root paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "Machine_Learning" / "artifacts"
METADATA_DIR = PROJECT_ROOT / "Machine_Learning" / "model_metadata"


class ClinicalInferenceError(Exception):
    """Base exception for clinical inference pipeline."""
    pass


class UnsupportedTaskError(ClinicalInferenceError):
    """Raised when an unsupported prediction task is requested."""
    pass


class ValidationError(ClinicalInferenceError):
    """Raised when input features fail schema, range, or missingness checks."""
    pass


class ModelArtifactNotFoundError(ClinicalInferenceError):
    """Raised when a required model artifact cannot be found on disk."""
    pass


# Supported task definitions and configuration
SUPPORTED_TASKS = {
    "coronary_artery_disease": {
        "alias": ["heart_disease", "cad", "coronary_artery_disease"],
        "artifact_file": "heart_disease_pipeline_v1.joblib",
        "metadata_file": "heart_disease.json",
        "score_type": "calibrated_probability",
        "is_probability_calibrated": True,
        "required_features": [
            "age", "sex", "cp", "trestbps", "chol", "fbs",
            "restecg", "thalch", "exang", "oldpeak", "slope", "ca", "thal"
        ],
        "numeric_bounds": {
            "age": (18, 120),
            "trestbps": (50, 260),
            "chol": (0, 700),  # 0 indicates unmeasured in legacy European cohorts
            "thalch": (50, 240),
            "thalach": (50, 240),
            "oldpeak": (-3.0, 10.0),
            "ca": (0, 3),
        },
        "categorical_valid": {
            "sex": ["Male", "Female"],
            "cp": ["typical angina", "atypical angina", "non-anginal", "asymptomatic"],
            "fbs": [True, False, 1, 0, "True", "False"],
            "restecg": ["normal", "lv hypertrophy", "st-t abnormality"],
            "exang": [True, False, 1, 0, "True", "False"],
            "slope": ["upsloping", "flat", "downsloping"],
            "thal": ["normal", "fixed defect", "reversable defect"],
        },
    },
    "heart_failure_mortality": {
        "alias": ["heart_failure_mortality", "hf_mortality", "heart_failure_risk"],
        "artifact_file": "heart_failure_pipeline_v1.joblib",
        "metadata_file": "heart_failure.json",
        "score_type": "classifier_confidence_score",
        "is_probability_calibrated": False,
        "required_features": [
            "age", "anaemia", "creatinine_phosphokinase", "diabetes",
            "ejection_fraction", "high_blood_pressure", "platelets",
            "serum_creatinine", "serum_sodium", "sex", "smoking"
        ],
        "numeric_bounds": {
            "age": (18, 120),
            "creatinine_phosphokinase": (10, 10000),
            "ejection_fraction": (10, 80),
            "platelets": (10000, 1500000),
            "serum_creatinine": (0.1, 15.0),
            "serum_sodium": (100, 175),
        },
        "categorical_valid": {
            "anaemia": [0, 1, True, False],
            "diabetes": [0, 1, True, False],
            "high_blood_pressure": [0, 1, True, False],
            "sex": [0, 1, "Male", "Female", "0", "1"],
            "smoking": [0, 1, True, False],
        },
    },
    "arrhythmia_ecg": {
        "alias": ["arrhythmia_ecg", "arrhythmia", "ecg_classification"],
        "artifact_file": "arrhythmia_pipeline_v1.joblib",
        "metadata_file": "arrhythmia.json",
        "score_type": "multiclass_class_probability_vector",
        "is_probability_calibrated": False,
        "required_features_count": 279,
    },
}

# Explicitly unsupported tasks with clinical justification
UNSUPPORTED_TASKS = {
    "heart_failure_screening": (
        "UNSUPPORTED TASK: Heart failure screening or diagnosis in the general population. "
        "The underlying dataset (heart_failure.csv) contains exclusively hospitalized patients "
        "with confirmed NYHA Class III-IV heart failure. There are NO non-heart-failure controls. "
        "Predicting heart failure occurrence from this dataset is medically invalid."
    ),
    "heart_failure_diagnosis": (
        "UNSUPPORTED TASK: Heart failure diagnosis. The available model predicts all-cause mortality "
        "during follow-up among already-diagnosed heart failure patients (DEATH_EVENT), NOT "
        "whether an unselected individual has heart failure."
    ),
    "arrhythmia_symptom_screening": (
        "UNSUPPORTED TASK: Arrhythmia screening from patient symptoms or routine vitals alone. "
        "The UCI Arrhythmia model requires 279 precomputed 12-lead ECG measurements (wave intervals, "
        "amplitudes, and vector angles across leads DI-V6). It cannot screen for arrhythmia "
        "from symptoms such as palpitations or dizziness."
    ),
    "ecg_waveform_analysis": (
        "UNSUPPORTED TASK: Direct raw ECG signal/waveform or image/PDF analysis. "
        "The system accepts precomputed numerical features only, not timeseries or raw voltage signals."
    ),
}

# Module-level model cache to avoid repeated disk reads
_MODEL_CACHE: Dict[str, Any] = {}
_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


def resolve_canonical_task(task_name: str) -> str:
    """Resolve an incoming task name or alias to its canonical key."""
    normalized = task_name.strip().lower()
    for canonical, cfg in SUPPORTED_TASKS.items():
        if normalized in cfg["alias"]:
            return canonical
    return normalized


def load_model_and_metadata(canonical_task: str) -> Tuple[Any, Dict[str, Any]]:
    """
    Load model pipeline and metadata from disk, utilizing memory caching.
    
    Parameters
    ----------
    canonical_task : str
        Canonical task key.
        
    Returns
    -------
    pipeline : sklearn.pipeline.Pipeline
        Fitted pipeline.
    metadata : dict
        Associated model metadata dictionary.
        
    Raises
    ------
    ModelArtifactNotFoundError
        If the artifact or metadata file is missing on disk.
    """
    if canonical_task in _MODEL_CACHE and canonical_task in _METADATA_CACHE:
        return _MODEL_CACHE[canonical_task], _METADATA_CACHE[canonical_task]

    task_cfg = SUPPORTED_TASKS[canonical_task]
    artifact_path = ARTIFACTS_DIR / task_cfg["artifact_file"]
    metadata_path = METADATA_DIR / task_cfg["metadata_file"]

    if not artifact_path.exists():
        raise ModelArtifactNotFoundError(
            f"Model artifact not found at {artifact_path}. Please execute the corresponding "
            f"training pipeline before requesting inference."
        )

    if not metadata_path.exists():
        raise ModelArtifactNotFoundError(
            f"Model metadata not found at {metadata_path}."
        )

    pipeline = joblib.load(artifact_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    _MODEL_CACHE[canonical_task] = pipeline
    _METADATA_CACHE[canonical_task] = metadata

    return pipeline, metadata


def validate_input_features(
    canonical_task: str,
    input_data: Union[Dict[str, Any], pd.DataFrame],
) -> pd.DataFrame:
    """
    Validate input schema, data types, missingness, and numeric bounds.
    
    NEVER silently imputes missing fields.
    
    Parameters
    ----------
    canonical_task : str
        Target prediction task.
    input_data : dict or pd.DataFrame
        Input clinical measurements.
        
    Returns
    -------
    pd.DataFrame
        Validated single- or multi-row DataFrame ready for pipeline transformation.
        
    Raises
    ------
    ValidationError
        If missing fields, invalid categories, or out-of-bounds numbers are detected.
    """
    if isinstance(input_data, dict):
        df = pd.DataFrame([input_data])
    elif isinstance(input_data, pd.DataFrame):
        df = input_data.copy()
    else:
        raise ValidationError(f"Expected dict or pandas DataFrame, got {type(input_data).__name__}")

    if df.empty:
        raise ValidationError("Input clinical payload is empty.")

    task_cfg = SUPPORTED_TASKS[canonical_task]

    # Arrhythmia special case (279 precomputed ECG features)
    if canonical_task == "arrhythmia_ecg":
        if df.shape[1] < 279:
            raise ValidationError(
                f"Arrhythmia ECG classification requires at least 279 precomputed ECG features. "
                f"Received {df.shape[1]} features. Symptom-only inputs are unsupported."
            )
        # Check for NaN / missing values
        null_counts = df.isnull().sum().sum()
        if null_counts > 0:
            raise ValidationError(
                f"Arrhythmia input contains {null_counts} missing/null values across ECG features. "
                f"Silently filling missing clinical inputs is prohibited."
            )
        return df

    # For Coronary Artery Disease, symmetrically alias thalach and thalch
    if canonical_task == "coronary_artery_disease":
        if "thalach" in df.columns and "thalch" not in df.columns:
            df["thalch"] = df["thalach"]
        elif "thalch" in df.columns and "thalach" not in df.columns:
            df["thalach"] = df["thalch"]

    # Validation for Heart Disease and Heart Failure
    required_features = task_cfg["required_features"]
    missing_fields = [col for col in required_features if col not in df.columns]
    if missing_fields:
        raise ValidationError(
            f"Missing required clinical inputs: {missing_fields}. "
            f"Silently filling missing clinical inputs is prohibited."
        )

    # Check for null/missing values in required columns
    for col in required_features:
        if df[col].isnull().any():
            raise ValidationError(
                f"Input field '{col}' contains null/empty values. "
                f"All required clinical parameters must be explicitly provided."
            )

    # Check numeric bounds
    numeric_bounds = task_cfg.get("numeric_bounds", {})
    for col, (min_val, max_val) in numeric_bounds.items():
        if col in df.columns:
            try:
                vals = pd.to_numeric(df[col], errors="raise")
                out_of_bounds = (vals < min_val) | (vals > max_val)
                if out_of_bounds.any():
                    invalid_val = vals[out_of_bounds].iloc[0]
                    raise ValidationError(
                        f"Field '{col}' has value {invalid_val}, which is outside plausible "
                        f"clinical bounds [{min_val}, {max_val}]."
                    )
                df[col] = vals
            except ValueError as e:
                raise ValidationError(f"Field '{col}' could not be converted to numeric: {str(e)}")

    # Check categorical values
    categorical_valid = task_cfg.get("categorical_valid", {})
    for col, valid_options in categorical_valid.items():
        if col in df.columns:
            for val in df[col]:
                # Allow boolean/string equivalence
                if val not in valid_options:
                    # Check case-insensitive string match
                    if isinstance(val, str) and any(str(opt).lower() == val.lower() for opt in valid_options):
                        continue
                    raise ValidationError(
                        f"Field '{col}' has invalid value '{val}'. Allowed options: {valid_options}"
                    )

    return df


def predict_clinical_condition(
    task: str,
    input_data: Union[Dict[str, Any], pd.DataFrame],
    explain: bool = False,
    explain_top_k: int = 5,
) -> Dict[str, Any]:
    """
    Execute clinical inference through the unified prediction interface.
    
    Parameters
    ----------
    task : str
        Prediction task identifier or alias.
    input_data : dict or pd.DataFrame
        Patient measurements or diagnostic inputs.
    explain : bool, default=False
        Whether to generate local feature attributions.
    explain_top_k : int, default=5
        Number of top risk-increasing and risk-decreasing features to return.
        
    Returns
    -------
    dict
        Structured inference result containing model identification, target
        semantics, prediction, scores, confidence/calibration metadata,
        and clinical safety disclaimers.
        
    Raises
    ------
    UnsupportedTaskError
        If an unsupported clinical task is requested.
    ValidationError
        If inputs fail schema or clinical plausibility checks.
    ModelArtifactNotFoundError
        If the underlying model artifact is missing.
    """
    normalized_task = task.strip().lower()

    # Guard 1: Explicit check for unsupported tasks
    if normalized_task in UNSUPPORTED_TASKS:
        raise UnsupportedTaskError(UNSUPPORTED_TASKS[normalized_task])

    canonical_task = resolve_canonical_task(normalized_task)
    if canonical_task not in SUPPORTED_TASKS:
        raise UnsupportedTaskError(
            f"Unrecognized or unsupported task '{task}'. "
            f"Supported tasks: {list(SUPPORTED_TASKS.keys())}. "
            f"Never request surrogate predictions for unsupported clinical tasks."
        )

    # Guard 2: Schema and range validation (zero silent imputation)
    validated_df = validate_input_features(canonical_task, input_data)

    # Load model and metadata
    pipeline, metadata = load_model_and_metadata(canonical_task)
    task_cfg = SUPPORTED_TASKS[canonical_task]

    # Execute prediction through fitted pipeline
    try:
        raw_preds = pipeline.predict(validated_df)
        raw_pred_val = raw_preds[0]
        
        # Check if prediction is numeric or string
        try:
            pred_id = int(raw_pred_val)
            classes_meta = metadata.get("dataset", {}).get("classes", {})
            pred_label = classes_meta.get(str(pred_id), f"Class {pred_id}")
        except (ValueError, TypeError):
            pred_label = str(raw_pred_val)
            if hasattr(pipeline, "classes_"):
                pred_id = int(np.where(pipeline.classes_ == raw_pred_val)[0][0])
            else:
                pred_id = 0
    except Exception as e:
        raise ClinicalInferenceError(f"Prediction execution failed: {str(e)}")

    # Extract probabilities or decision scores
    scores_dict: Dict[str, Any] = {}
    calibrated_prob: Optional[float] = None
    raw_score: Optional[float] = None

    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(validated_df)[0]
        if len(probs) == 2:
            positive_prob = round(float(probs[1]), 4)
            raw_score = positive_prob
            if task_cfg["is_probability_calibrated"]:
                calibrated_prob = positive_prob
            scores_dict = {
                "negative_class_probability": round(float(probs[0]), 4),
                "positive_class_probability": positive_prob,
            }
        else:
            # Multiclass - map probabilities to pipeline class names
            if hasattr(pipeline, "classes_"):
                scores_dict = {
                    str(cls_name): round(float(probs[i]), 4)
                    for i, cls_name in enumerate(pipeline.classes_)
                }
            else:
                scores_dict = {f"Class_{i}": round(float(p), 4) for i, p in enumerate(probs)}
            raw_score = round(float(np.max(probs)), 4)
    elif hasattr(pipeline, "decision_function"):
        decision_val = float(pipeline.decision_function(validated_df)[0])
        raw_score = round(decision_val, 4)
        scores_dict = {"decision_function_score": raw_score}

    # Format result structure
    result: Dict[str, Any] = {
        "status": "success",
        "task": canonical_task,
        "task_scope": {
            "supported": True,
            "target_definition": metadata.get("dataset", {}).get("target_definition", ""),
            "intended_population": metadata.get("dataset", {}).get("name", ""),
        },
        "model_identification": {
            "model_name": metadata.get("model_name", "Clinical Classifier"),
            "version": metadata.get("version", "1.0.0"),
            "algorithm": metadata.get("training", {}).get("algorithm", "Unknown"),
        },
        "prediction": {
            "predicted_class_id": pred_id,
            "predicted_class_label": pred_label,
            "score": raw_score,
            "score_type": task_cfg["score_type"],
            "is_probability_calibrated": task_cfg["is_probability_calibrated"],
            "calibrated_probability": calibrated_prob,
            "decision_threshold": 0.5 if len(scores_dict) <= 2 else None,
            "class_probabilities": scores_dict,
        },
        "validation_status": {
            "is_valid": True,
            "features_checked_count": len(validated_df.columns),
        },
        "clinical_prototype_disclaimer": metadata.get(
            "clinical_prototype_disclaimer",
            "This model is a research and educational prototype. It is NOT certified as a "
            "diagnostic device. Predictions do NOT represent verified prospective patient risk."
        ),
        "limitations": [
            "Evaluations reflect retrospective dataset distributions and may not generalize to diverse populations.",
            "Predictions must not be used as the sole basis for clinical diagnosis or treatment alterations.",
            "Emergency presentations must be triaged according to emergency clinical guidelines immediately."
        ],
    }

    # Optional explainability
    if explain:
        try:
            explanation = explain_prediction_local(
                pipeline=pipeline,
                input_df=validated_df,
                top_k=explain_top_k,
                target_class_index=min(pred_id, 1),
            )
            result["explanation"] = explanation
        except Exception as e:
            result["explanation"] = {
                "status": "explanation_failed",
                "error": str(e),
                "non_causal_disclaimer": CAUSAL_DISCLAIMER,
            }

    return result
