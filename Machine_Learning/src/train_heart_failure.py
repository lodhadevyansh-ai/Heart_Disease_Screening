"""Heart Failure Mortality Risk Model Training Script.

Trains, evaluates, and persists candidate clinical outcome classifiers for the
Faisalabad Heart Failure clinical records dataset.

CRITICAL CLINICAL & ARCHITECTURAL REQUIREMENT:
The target is strictly `DEATH_EVENT` (all-cause mortality during follow-up).
This dataset contains exclusively patients with established heart failure (NYHA III-IV).
It does NOT support, and must NEVER be used for, heart failure screening or diagnosis.
Follow-up observation `time` is strictly excluded to prevent look-ahead target leakage.
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

from Machine_Learning.src.data_loader import load_heart_failure_data
from Machine_Learning.src.evaluate import evaluate_binary_classifier, print_evaluation_summary
from Machine_Learning.src.preprocessing import (
    HEART_FAILURE_RAW_FEATURES,
    DatasetSplits,
    prepare_heart_failure_splits,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_hf_candidate_models(random_state: int = 42) -> Dict[str, Any]:
    """Returns candidate classifiers for heart failure mortality prediction."""
    return {
        "Dummy (Stratified Baseline)": DummyClassifier(strategy="stratified", random_state=random_state),
        "Logistic Regression (Balanced)": LogisticRegression(
            C=0.5, class_weight="balanced", max_iter=1000, random_state=random_state
        ),
        "Random Forest (Depth 4)": RandomForestClassifier(
            n_estimators=100, max_depth=4, min_samples_split=4, class_weight="balanced", random_state=random_state
        ),
        "Gradient Boosting (Shallow)": GradientBoostingClassifier(
            n_estimators=80, learning_rate=0.04, max_depth=2, random_state=random_state
        ),
        "Support Vector Classifier (RBF)": SVC(
            kernel="rbf", C=0.8, probability=True, class_weight="balanced", random_state=random_state
        ),
    }


def train_and_select_best_hf_model(
    splits: DatasetSplits,
    random_state: int = 42,
) -> Tuple[str, Any, Dict[str, Dict[str, Any]]]:
    """Fits candidate models on training fold, evaluates on validation fold, and selects the best model.

    Returns:
        Tuple of (best_model_name, best_fitted_model, validation_results_dict)
    """
    candidates = get_hf_candidate_models(random_state)
    validation_results: Dict[str, Dict[str, Any]] = {}

    best_score = -1.0
    best_model_name = ""
    best_model_obj = None

    logger.info("Evaluating %d candidate models on Heart Failure validation fold...", len(candidates))

    for name, model in candidates.items():
        model.fit(splits.X_train, splits.y_train)

        y_val_pred = model.predict(splits.X_val)
        y_val_prob = model.predict_proba(splits.X_val)[:, 1] if hasattr(model, "predict_proba") else None

        val_metrics = evaluate_binary_classifier(splits.y_val, y_val_pred, y_val_prob)
        validation_results[name] = val_metrics

        val_score = val_metrics.get("roc_auc")
        if val_score is None:
            val_score = val_metrics.get("f1_score", 0.0)

        logger.info(
            "Candidate [%s]: Val ROC-AUC=%.4f, Val F1=%.4f, Val Balanced Acc=%.4f",
            name,
            val_metrics.get("roc_auc") or 0.0,
            val_metrics.get("f1_score", 0.0),
            val_metrics.get("balanced_accuracy", 0.0),
        )

        if val_score > best_score:
            best_score = val_score
            best_model_name = name
            best_model_obj = model

    logger.info("Selected top Heart Failure model: '%s' (Validation Score: %.4f)", best_model_name, best_score)
    return best_model_name, best_model_obj, validation_results


def run_hf_training_pipeline(
    random_seed: int = 42,
    artifacts_dir: Optional[Path | str] = None,
    metadata_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Full Heart Failure mortality outcome training pipeline."""
    art_dir = Path(artifacts_dir) if artifacts_dir else (PROJECT_ROOT / "Machine_Learning" / "artifacts")
    meta_dir = Path(metadata_dir) if metadata_dir else (PROJECT_ROOT / "Machine_Learning" / "model_metadata")
    art_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ingest raw dataset
    logger.info("Loading Heart Failure Clinical Records dataset...")
    df_raw = load_heart_failure_data()

    # 2. Prepare leakage-free splits (drops 'time' automatically)
    logger.info("Preparing stratified Train/Val/Test splits (seed=%d)...", random_seed)
    splits = prepare_heart_failure_splits(
        df_raw, test_size=0.2, val_size=0.1, random_state=random_seed
    )

    # 3. Model selection across validation fold
    best_name, best_model, val_results = train_and_select_best_hf_model(splits, random_state=random_seed)

    # 4. Final evaluation on held-out Test fold (applied only once)
    logger.info("Evaluating selected model '%s' on held-out Test fold (%d samples)...", best_name, len(splits.y_test))
    y_test_pred = best_model.predict(splits.X_test)
    y_test_prob = best_model.predict_proba(splits.X_test)[:, 1] if hasattr(best_model, "predict_proba") else None
    test_metrics = evaluate_binary_classifier(splits.y_test, y_test_pred, y_test_prob)

    print_evaluation_summary(test_metrics, f"HELD-OUT TEST SET: {best_name}")

    # 5. Assemble unified end-to-end inference pipeline
    inference_pipeline = Pipeline(steps=[
        ("preprocessor", splits.preprocessor),
        ("classifier", best_model),
    ])

    # 6. Save serialized artifact
    artifact_filename = "heart_failure_pipeline_v1.joblib"
    artifact_path = art_dir / artifact_filename
    joblib.dump(inference_pipeline, artifact_path)
    logger.info("Saved unified model artifact to: %s", artifact_path.resolve())

    # 7. Compile structured metadata documenting task specificity
    metadata_payload = {
        "model_name": "Heart Failure Follow-up Mortality Risk Stratifier",
        "version": "1.0.0",
        "artifact_path": str(artifact_path.relative_to(PROJECT_ROOT)),
        "dataset": {
            "name": "Heart Failure Clinical Records",
            "file": "Machine_Learning/datasets/raw/heart_failure.csv",
            "total_records": len(df_raw),
            "target_column": "DEATH_EVENT",
            "target_definition": "All-cause mortality during post-admission follow-up among confirmed NYHA Class III-IV heart failure patients",
            "classes": {
                "0": "Survived Follow-up Period",
                "1": "Deceased During Follow-up Period"
            },
        },
        "task_feasibility_and_scope": {
            "supported_task": "Prognostic mortality risk stratification for patients with diagnosed heart failure",
            "unsupported_tasks": [
                "heart_failure_screening",
                "heart_failure_diagnosis",
                "incidence_prediction_in_healthy_cohorts"
            ],
            "clinical_task_mismatch_justification": (
                "The dataset contains exclusively hospitalized patients with confirmed NYHA Class III-IV heart failure. "
                "There are no healthy or non-heart-failure controls. Relabeling DEATH_EVENT as a heart-failure diagnostic "
                "prediction is medically invalid and violates Rule 8."
            ),
            "data_leakage_safeguards": (
                "Follow-up duration (column 'time') was strictly excluded from predictors because future observation "
                "duration is unknown at clinical intake."
            ),
            "sample_size_uncertainty": (
                "Small cohort (N=299, 96 death events). Measured test performance has wide confidence intervals and "
                "reflects single-institution selection bias."
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
            "raw_input_features": HEART_FAILURE_RAW_FEATURES,
            "excluded_features": ["time"],
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

    metadata_path = meta_dir / "heart_failure.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)
    logger.info("Saved model metadata to: %s", metadata_path.resolve())

    return metadata_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and evaluate Heart Failure mortality prediction model.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Directory to save model artifacts.")
    parser.add_argument("--metadata-dir", type=str, default=None, help="Directory to save metadata JSON.")
    args = parser.parse_args()

    results = run_hf_training_pipeline(
        random_seed=args.random_seed,
        artifacts_dir=args.artifacts_dir,
        metadata_dir=args.metadata_dir,
    )
    print("Heart failure training process finished successfully.")
