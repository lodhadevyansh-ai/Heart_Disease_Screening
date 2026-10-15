"""Preprocessing Pipelines for Cardiovascular Clinical Datasets.

This module provides separate, leakage-free scikit-learn preprocessing pipelines
for each of the three clinical datasets:
1. Heart Disease (UCI)
2. Heart Failure Clinical Records
3. Arrhythmia Conditions

Key architectural principles enforced:
- Learned transformations (imputers, scalers, one-hot encoders) are fitted EXCLUSIVELY on training splits.
- Patient identifiers (`id`) and site variables (`dataset`) are excluded from predictive models.
- Target look-ahead leakage is prevented: follow-up `time` in Heart Failure is excluded from prospective predictors.
- Physiological missing zeros (`chol == 0`, `trestbps == 0`) are converted to NaN and imputed with median values.
- Inference pipelines use identical feature ordering, transformations, and handle unexpected categories gracefully.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler

from Machine_Learning.src.feature_engineering import (
    ArrhythmiaFeatureEngineer,
    HeartDiseaseFeatureEngineer,
    HeartFailureFeatureEngineer,
)

logger = logging.getLogger(__name__)

# Base expected input feature schemas for prospective inference
HEART_DISEASE_RAW_FEATURES = [
    "age", "sex", "cp", "trestbps", "chol", "fbs",
    "restecg", "thalch", "exang", "oldpeak", "slope", "ca", "thal"
]

HEART_FAILURE_RAW_FEATURES = [
    "age", "anaemia", "creatinine_phosphokinase", "diabetes",
    "ejection_fraction", "high_blood_pressure", "platelets",
    "serum_creatinine", "serum_sodium", "sex", "smoking"
]


class HeartDiseaseCleaner(BaseEstimator, TransformerMixin):
    """Replaces unmeasured clinical zeros in cholesterol and blood pressure with NaN."""

    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> HeartDiseaseCleaner:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        if "chol" in df.columns:
            df["chol"] = df["chol"].replace(0, np.nan)
        if "trestbps" in df.columns:
            df["trestbps"] = df["trestbps"].replace(0, np.nan)
        return df


class ArrhythmiaCleaner(BaseEstimator, TransformerMixin):
    """Drops feature 13 (83.3% missing) and caps physiological height outliers."""

    def __init__(self, drop_feature_13: bool = True):
        self.drop_feature_13 = drop_feature_13

    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> ArrhythmiaCleaner:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        if self.drop_feature_13 and "13" in df.columns:
            df = df.drop(columns=["13"])
        if "2" in df.columns:
            df.loc[df["2"].astype(float) > 250.0, "2"] = np.nan
        return df


@dataclass
class DatasetSplits:
    """Container for split data arrays, fitted preprocessor, and output feature metadata."""
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    preprocessor: Pipeline
    feature_names_out: List[str]
    target_name: str
    metadata: Dict[str, Any]


def build_heart_disease_preprocessor() -> Pipeline:
    """Builds a complete scikit-learn preprocessing pipeline for UCI Heart Disease.

    Numeric features: Imputed via median, scaled via RobustScaler.
    Categorical features: Imputed via most-frequent, encoded via OneHotEncoder(handle_unknown='ignore').
    Feature Engineering: Chronotropic incompetence ratio, ST depression indicator, age tiers.
    """
    numeric_features = [
        "age", "trestbps", "chol", "thalch", "oldpeak", "ca",
        "max_hr_ratio", "chronotropic_incompetence", "st_depression_significant", "age_ge_60"
    ]
    categorical_features = ["sex", "cp", "fbs", "restecg", "exang", "slope", "thal"]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", RobustScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    col_transformer = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    full_pipeline = Pipeline(steps=[
        ("cleaner", HeartDiseaseCleaner()),
        ("feat_eng", HeartDiseaseFeatureEngineer()),
        ("col_transform", col_transformer),
    ])

    return full_pipeline


def build_heart_failure_preprocessor() -> Pipeline:
    """Builds a complete scikit-learn preprocessing pipeline for Heart Failure records.

    Numeric features: Imputed via median, standardized via StandardScaler.
    Binary/Categorical features: Imputed via most-frequent.
    Feature Engineering: Ejection fraction clinical tiers, renal dysfunction, cardiorenal synergy.
    """
    numeric_features = [
        "age", "creatinine_phosphokinase", "ejection_fraction",
        "platelets", "serum_creatinine", "serum_sodium"
    ]
    binary_features = [
        "anaemia", "diabetes", "high_blood_pressure", "sex", "smoking",
        "reduced_ef", "severe_ef_reduction", "renal_dysfunction",
        "cardiorenal_risk", "hypertension_elderly"
    ]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    binary_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
    ])

    col_transformer = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("bin", binary_transformer, binary_features),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    full_pipeline = Pipeline(steps=[
        ("feat_eng", HeartFailureFeatureEngineer()),
        ("col_transform", col_transformer),
    ])

    return full_pipeline


def build_arrhythmia_preprocessor(feature_columns: List[str]) -> Pipeline:
    """Builds a preprocessing pipeline for 12-lead ECG Arrhythmia features.

    Drops feature 13 (high missingness), engineers QTc and conduction flags,
    and applies median imputation and standard scaling.
    """
    pipeline = Pipeline(steps=[
        ("cleaner", ArrhythmiaCleaner(drop_feature_13=True)),
        ("feat_eng", ArrhythmiaFeatureEngineer(add_qtc=True, add_conduction_flags=True)),
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    return pipeline


def prepare_heart_disease_splits(
    df: pd.DataFrame,
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42,
    target_mode: str = "binary"
) -> DatasetSplits:
    """Splits Heart Disease data into Train, Validation, and Test sets, fitting preprocessing on Train only.

    Args:
        df: Raw Heart Disease DataFrame.
        test_size: Test proportion.
        val_size: Validation proportion relative to total.
        random_state: Reproducible seed.
        target_mode: 'binary' (num > 0) or 'multiclass' (num: 0-4).

    Returns:
        DatasetSplits: Structured splits with preprocessor fitted on Train only.
    """
    df_clean = df.copy()

    # Drop non-predictive site artifacts and patient id
    cols_to_drop = ["id", "dataset"]
    df_clean = df_clean.drop(columns=[col for col in cols_to_drop if col in df_clean.columns])

    # Formulate target
    if target_mode == "binary":
        y = (df_clean["num"] > 0).astype(int).values
        target_name = "cad_presence"
    else:
        y = df_clean["num"].values
        target_name = "cad_severity_stage"

    X = df_clean.drop(columns=["num"])

    # First split: Hold out Test set with stratification
    test_ratio = test_size
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_ratio, random_state=random_state, stratify=y
    )

    # Second split: Train vs Validation
    val_ratio_adjusted = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio_adjusted, random_state=random_state, stratify=y_temp
    )

    # Build and fit preprocessor strictly on training data
    pipeline = build_heart_disease_preprocessor()
    X_train_trans = pipeline.fit_transform(X_train)
    X_val_trans = pipeline.transform(X_val)
    X_test_trans = pipeline.transform(X_test)

    # Extract feature names
    col_trans: ColumnTransformer = pipeline.named_steps["col_transform"]
    feature_names = list(col_trans.get_feature_names_out())

    return DatasetSplits(
        X_train=X_train_trans,
        y_train=y_train,
        X_val=X_val_trans,
        y_val=y_val,
        X_test=X_test_trans,
        y_test=y_test,
        preprocessor=pipeline,
        feature_names_out=feature_names,
        target_name=target_name,
        metadata={
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "test_samples": len(y_test),
            "target_mode": target_mode,
            "raw_features": HEART_DISEASE_RAW_FEATURES,
        }
    )


def prepare_heart_failure_splits(
    df: pd.DataFrame,
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42
) -> DatasetSplits:
    """Splits Heart Failure records into Train/Val/Test, strictly removing follow-up `time` to prevent leakage.

    Args:
        df: Raw Heart Failure DataFrame.
        test_size: Test proportion.
        val_size: Validation proportion relative to total.
        random_state: Reproducible seed.

    Returns:
        DatasetSplits: Structured splits with preprocessor fitted on Train only.
    """
    df_clean = df.copy()

    # CRITICAL LEAKAGE REMOVAL: drop follow-up observation time
    if "time" in df_clean.columns:
        df_clean = df_clean.drop(columns=["time"])

    y = df_clean["DEATH_EVENT"].values
    X = df_clean.drop(columns=["DEATH_EVENT"])

    # Stratified Train/Val/Test split
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    val_ratio_adjusted = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio_adjusted, random_state=random_state, stratify=y_temp
    )

    # Fit preprocessor strictly on training data
    pipeline = build_heart_failure_preprocessor()
    X_train_trans = pipeline.fit_transform(X_train)
    X_val_trans = pipeline.transform(X_val)
    X_test_trans = pipeline.transform(X_test)

    col_trans: ColumnTransformer = pipeline.named_steps["col_transform"]
    feature_names = list(col_trans.get_feature_names_out())

    return DatasetSplits(
        X_train=X_train_trans,
        y_train=y_train,
        X_val=X_val_trans,
        y_val=y_val,
        X_test=X_test_trans,
        y_test=y_test,
        preprocessor=pipeline,
        feature_names_out=feature_names,
        target_name="death_event_mortality",
        metadata={
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "test_samples": len(y_test),
            "raw_features": HEART_FAILURE_RAW_FEATURES,
        }
    )


def prepare_arrhythmia_splits(
    df: pd.DataFrame,
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42
) -> DatasetSplits:
    """Splits Arrhythmia dataset with stratified handling for imbalanced multi-class targets."""
    df_clean = df.copy()
    y = np.array(df_clean["condition_group"].tolist())
    X = df_clean.drop(columns=["condition_group"])

    # Stratified split: Structural_Atrial_Abnormality has only 9 instances
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    val_ratio_adjusted = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio_adjusted, random_state=random_state, stratify=y_temp
    )

    # Build and fit pipeline strictly on X_train
    pipeline = build_arrhythmia_preprocessor(list(X_train.columns))
    X_train_trans = pipeline.fit_transform(X_train)
    X_val_trans = pipeline.transform(X_val)
    X_test_trans = pipeline.transform(X_test)

    # Generate feature names from pipeline transformer
    feat_eng: ArrhythmiaFeatureEngineer = pipeline.named_steps["feat_eng"]
    feature_names = list(feat_eng.get_feature_names_out())

    return DatasetSplits(
        X_train=X_train_trans,
        y_train=y_train,
        X_val=X_val_trans,
        y_val=y_val,
        X_test=X_test_trans,
        y_test=y_test,
        preprocessor=pipeline,
        feature_names_out=feature_names,
        target_name="condition_group",
        metadata={
            "train_samples": len(y_train),
            "val_samples": len(y_val),
            "test_samples": len(y_test),
            "classes": sorted(list(np.unique(y))),
        }
    )


def preprocess_inference_input(
    input_data: Union[pd.DataFrame, Dict[str, Any]],
    preprocessor: Pipeline,
    expected_features: List[str]
) -> np.ndarray:
    """Applies a trained preprocessing pipeline to inference data with rigorous schema validation.

    Args:
        input_data: Dictionary of patient inputs or pandas DataFrame.
        preprocessor: Fitted scikit-learn Pipeline.
        expected_features: List of required feature names in expected order.

    Returns:
        np.ndarray: Transformed features ready for model prediction.
    """
    if isinstance(input_data, dict):
        df = pd.DataFrame([input_data])
    elif isinstance(input_data, pd.DataFrame):
        df = input_data.copy()
    else:
        raise TypeError("Inference input must be a dict or pandas DataFrame.")

    # Validate that expected features are present; populate missing with NaN for median/mode imputer
    for feat in expected_features:
        if feat not in df.columns:
            logger.warning("Feature '%s' missing from inference input; populating with NaN for imputer.", feat)
            df[feat] = np.nan

    # Ensure consistent column ordering before transforming
    df = df[expected_features]

    # Transform using fitted pipeline (no fitting allowed)
    transformed = preprocessor.transform(df)
    return transformed
