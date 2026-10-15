"""Arrhythmia Multi-Class Model Training Script.

Trains, evaluates, and persists candidate multi-class classification models for the
UCI Arrhythmia database across 5 cardiac condition groups.

CRITICAL CLINICAL & ARCHITECTURAL REQUIREMENT:
The inputs to this model are 279 PRECOMPUTED 12-LEAD ECG WAVEFORM PARAMETERS.
This model DOES NOT, and CANNOT, predict arrhythmia from patient symptoms or routine labs.
It cannot parse raw ECG waveform audio/signals or scanned PDF reports.
Screening pipelines must mark symptom-only prediction as UNSUPPORTED.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

# Ensure repository root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Machine_Learning.src.data_loader import load_arrhythmia_data
from Machine_Learning.src.evaluate import evaluate_multiclass_classifier, print_multiclass_summary
from Machine_Learning.src.preprocessing import (
    DatasetSplits,
    prepare_arrhythmia_splits,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_arrhythmia_candidate_models(random_state: int = 42) -> Dict[str, Any]:
    """Returns candidate multi-class classifiers for ECG waveform classification."""
    return {
        "Dummy (Stratified Baseline)": DummyClassifier(strategy="stratified", random_state=random_state),
        "Logistic Regression (Balanced)": LogisticRegression(
            C=0.5, class_weight="balanced", max_iter=1000, random_state=random_state
        ),
        "Random Forest (Depth 6 Balanced)": RandomForestClassifier(
            n_estimators=150, max_depth=6, min_samples_split=4, class_weight="balanced", random_state=random_state
        ),
        "Gradient Boosting (Multiclass)": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=3, random_state=random_state
        ),
        "Support Vector Classifier (RBF Balanced)": SVC(
            kernel="rbf", C=1.2, probability=True, class_weight="balanced", random_state=random_state
        ),
    }


def train_and_select_best_arrhythmia_model(
    splits: DatasetSplits,
    random_state: int = 42,
) -> Tuple[str, Any, Dict[str, Dict[str, Any]]]:
    """Fits candidate multi-class models on training fold, evaluates on validation fold, and selects the best model.

    Primary selection metric: Macro-F1 / Balanced Accuracy (due to extreme class imbalance).
    """
    candidates = get_arrhythmia_candidate_models(random_state)
    validation_results: Dict[str, Dict[str, Any]] = {}

    best_score = -1.0
    best_model_name = ""
    best_model_obj = None

    classes = sorted(list(np.unique(splits.y_train)))
    logger.info("Evaluating %d candidate models on Arrhythmia validation fold across %d classes...", len(candidates), len(classes))

    for name, model in candidates.items():
        model.fit(splits.X_train, splits.y_train)

        y_val_pred = model.predict(splits.X_val)
        y_val_prob = model.predict_proba(splits.X_val) if hasattr(model, "predict_proba") else None

        val_metrics = evaluate_multiclass_classifier(splits.y_val, y_val_pred, y_val_prob, class_labels=classes)
        validation_results[name] = val_metrics

        # Primary selection: Balanced Accuracy (Macro Recall) to ensure rare classes are evaluated fairly
        val_score = val_metrics.get("balanced_accuracy", 0.0)

        logger.info(
            "Candidate [%s]: Val Balanced Acc=%.4f, Val Macro F1=%.4f, Val Accuracy=%.4f",
            name,
            val_metrics.get("balanced_accuracy", 0.0),
            val_metrics.get("macro_f1", 0.0),
            val_metrics.get("accuracy", 0.0),
        )

        if val_score > best_score:
            best_score = val_score
            best_model_name = name
            best_model_obj = model

    logger.info("Selected top Arrhythmia model: '%s' (Validation Balanced Accuracy: %.4f)", best_model_name, best_score)
    return best_model_name, best_model_obj, validation_results


def run_arrhythmia_training_pipeline(
    random_seed: int = 42,
    artifacts_dir: Optional[Path | str] = None,
    metadata_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Full Arrhythmia training pipeline execution."""
    art_dir = Path(artifacts_dir) if artifacts_dir else (PROJECT_ROOT / "Machine_Learning" / "artifacts")
    meta_dir = Path(metadata_dir) if metadata_dir else (PROJECT_ROOT / "Machine_Learning" / "model_metadata")
    art_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ingest raw dataset
    logger.info("Loading Arrhythmia Conditions dataset...")
    df_raw = load_arrhythmia_data()

    # 2. Prepare stratified splits (drops feature 13, cleans height outlier)
    logger.info("Preparing stratified Train/Val/Test splits (seed=%d)...", random_seed)
    splits = prepare_arrhythmia_splits(
        df_raw, test_size=0.2, val_size=0.1, random_state=random_seed
    )

    classes = sorted(list(np.unique(splits.y_train)))

    # 3. Model selection across validation fold
    best_name, best_model, val_results = train_and_select_best_arrhythmia_model(splits, random_state=random_seed)

    # 4. Final evaluation on held-out Test fold
    logger.info("Evaluating selected model '%s' on held-out Test fold (%d samples)...", best_name, len(splits.y_test))
    y_test_pred = best_model.predict(splits.X_test)
    y_test_prob = best_model.predict_proba(splits.X_test) if hasattr(best_model, "predict_proba") else None
    test_metrics = evaluate_multiclass_classifier(splits.y_test, y_test_pred, y_test_prob, class_labels=classes)

    print_multiclass_summary(test_metrics, f"HELD-OUT TEST SET: {best_name}")

    # 5. Assemble unified end-to-end inference pipeline
    inference_pipeline = Pipeline(steps=[
        ("preprocessor", splits.preprocessor),
        ("classifier", best_model),
    ])

    # 6. Save serialized artifact
    artifact_filename = "arrhythmia_pipeline_v1.joblib"
    artifact_path = art_dir / artifact_filename
    joblib.dump(inference_pipeline, artifact_path)
    logger.info("Saved unified model artifact to: %s", artifact_path.resolve())

    # 7. Compile structured metadata documenting task specificity
    metadata_payload = {
        "model_name": "Cardiac Arrhythmia 12-Lead ECG Classifier",
        "version": "1.0.0",
        "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
        "dataset": {
            "name": "UCI Arrhythmia Database",
            "file": "Machine_Learning/datasets/raw/arrhythmia_conditions.csv",
            "total_records": len(df_raw),
            "total_raw_columns": df_raw.shape[1],
            "target_column": "condition_group",
            "class_distribution": {str(k): int(v) for k, v in df_raw["condition_group"].value_counts().items()},
        },
        "task_feasibility_and_scope": {
            "supported_task": "Multi-class categorization of precomputed 12-lead ECG waveform measurements",
            "unsupported_tasks": [
                "symptom_based_arrhythmia_screening",
                "routine_laboratory_arrhythmia_prediction",
                "raw_ecg_signal_interpretation",
                "image_ecg_report_parsing"
            ],
            "input_modality_requirements": (
                "The model requires 279 precomputed quantitative numerical features extracted from a 12-lead ECG "
                "(wave intervals, vector angles, and waveform deflections across leads DI-V6). It cannot predict "
                "arrhythmia from patient symptom reports (palpitations, dizziness) or standard vital signs."
            ),
            "rare_class_uncertainty": (
                "The class 'Structural_Atrial_Abnormality' contains only 9 instances in the entire dataset (test fold n=2). "
                "Performance estimates for this class have substantial variance."
            ),
        },
        "training": {
            "algorithm": best_name,
            "hyperparameters": {k: str(v) for k, v in best_model.get_params().items()},
            "random_seed": random_seed,
            "split_ratio": {"train": 0.70, "val": 0.10, "test": 0.20},
            "train_samples": len(splits.y_train),
            "val_samples": len(splits.y_val),
            "test_samples": len(splits.y_test),
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "feature_schema": {
            "raw_feature_count": 279,
            "excluded_features": ["13"],
            "transformed_features": splits.feature_names_out,
            "transformed_feature_count": len(splits.feature_names_out),
        },
        "validation_model_comparison": val_results,
        "measured_test_metrics": test_metrics,
        "clinical_prototype_disclaimer": (
            "This model is a research and educational prototype. It is NOT certified as a diagnostic device. "
            "Evaluations reflect retrospective dataset performance and do NOT represent verified prospective patient risk."
        ),
    }

    metadata_path = meta_dir / "arrhythmia.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)
    logger.info("Saved model metadata to: %s", metadata_path.resolve())

    return metadata_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and evaluate Arrhythmia multi-class prediction model.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Directory to save model artifacts.")
    parser.add_argument("--metadata-dir", type=str, default=None, help="Directory to save metadata JSON.")
    args = parser.parse_args()

    results = run_arrhythmia_training_pipeline(
        random_seed=args.random_seed,
        artifacts_dir=args.artifacts_dir,
        metadata_dir=args.metadata_dir,
    )
    print("Arrhythmia training process finished successfully.")
