"""Data Loader Module for Heart Disease Screening and Condition-Risk Prediction System.

This module provides reusable, robust loaders and schema validators for the three
screening and clinical risk datasets:
1. Heart Disease (UCI)
2. Heart Failure Clinical Records
3. Arrhythmia Conditions

All loaders validate file existence, ensure proper schema conformity, check data
integrity (missingness, duplicates, outliers), and guarantee that raw data on disk
is never mutated.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Base directory for raw datasets
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DATA_DIR = PROJECT_ROOT / "Machine_Learning" / "datasets" / "raw"

# Expected schema definitions based on actual dataset inspection
HEART_DISEASE_UCI_COLUMNS = [
    "id", "age", "sex", "dataset", "cp", "trestbps", "chol", "fbs",
    "restecg", "thalch", "exang", "oldpeak", "slope", "ca", "thal", "num"
]

HEART_FAILURE_COLUMNS = [
    "age", "anaemia", "creatinine_phosphokinase", "diabetes",
    "ejection_fraction", "high_blood_pressure", "platelets",
    "serum_creatinine", "serum_sodium", "sex", "smoking", "time", "DEATH_EVENT"
]

ARRHYTHMIA_FEATURE_COUNT = 279  # Columns '0' to '278'
ARRHYTHMIA_COLUMNS = [str(i) for i in range(ARRHYTHMIA_FEATURE_COUNT)] + ["condition_group"]


class DatasetError(Exception):
    """Base exception for data loading errors."""


class DatasetNotFoundError(DatasetError):
    """Raised when a dataset file does not exist at the specified path."""


class MalformedDatasetError(DatasetError):
    """Raised when a dataset cannot be parsed or is corrupted."""


class DatasetValidationError(DatasetError):
    """Raised when a dataset fails schema or integrity validation."""


@dataclass(frozen=True)
class DatasetAuditReport:
    """Comprehensive statistical audit report for a loaded dataset."""
    dataset_name: str
    file_path: str
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: List[str]
    dtypes: Dict[str, str]
    missing_values: Dict[str, int]
    missing_percentages: Dict[str, float]
    target_column: Optional[str]
    target_distribution: Optional[Dict[str, int]]
    anomalies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_dataframe(
    df: pd.DataFrame,
    dataset_name: str,
    file_path: str,
    target_col: Optional[str] = None
) -> DatasetAuditReport:
    """Performs an extensive, non-destructive audit of a loaded DataFrame.

    Args:
        df: The pandas DataFrame to inspect.
        dataset_name: Identifier name of the dataset.
        file_path: Source file path string.
        target_col: Optional target column to analyze class distribution.

    Returns:
        DatasetAuditReport: Structured audit metadata.
    """
    row_count, col_count = df.shape
    dup_count = int(df.duplicated().sum())

    dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    missing_counts = df.isnull().sum()
    missing_vals = {col: int(cnt) for col, cnt in missing_counts.items() if cnt > 0}
    missing_pcts = {col: round(float(cnt / row_count) * 100, 2) for col, cnt in missing_vals.items()}

    target_dist: Optional[Dict[str, int]] = None
    if target_col and target_col in df.columns:
        target_dist = {str(k): int(v) for k, v in df[target_col].value_counts(dropna=False).items()}

    anomalies: List[str] = []

    # Domain-specific anomaly scans based on actual dataset observations
    if dataset_name == "heart_disease_uci":
        if "chol" in df.columns:
            zero_chol = int((df["chol"] == 0).sum())
            if zero_chol > 0:
                anomalies.append(f"chol has {zero_chol} physiologically impossible zero-values (missing data encoded as 0)")
        if "trestbps" in df.columns:
            zero_bps = int((df["trestbps"] == 0).sum())
            if zero_bps > 0:
                anomalies.append(f"trestbps has {zero_bps} physiologically impossible zero-values")

    elif dataset_name == "heart_failure":
        if "time" in df.columns:
            anomalies.append("Column 'time' is follow-up duration (days); risk of look-ahead leakage for baseline screening")
        if target_col == "DEATH_EVENT":
            anomalies.append("Target 'DEATH_EVENT' denotes mortality in established heart failure, NOT heart failure diagnosis")

    elif dataset_name == "arrhythmia_conditions":
        if "13" in df.columns and df["13"].isnull().sum() > 0:
            anomalies.append(f"Feature '13' (J-angle) has high missingness: {df['13'].isnull().sum()} / {row_count} ({round(df['13'].isnull().sum()/row_count*100, 1)}%)")
        if "2" in df.columns:
            height_outliers = int((df["2"] > 250).sum())
            if height_outliers > 0:
                anomalies.append(f"Feature '2' (Height) contains extreme values up to {df['2'].max()} cm (likely data entry error)")

    return DatasetAuditReport(
        dataset_name=dataset_name,
        file_path=file_path,
        row_count=row_count,
        column_count=col_count,
        duplicate_rows=dup_count,
        columns=list(df.columns),
        dtypes=dtypes,
        missing_values=missing_vals,
        missing_percentages=missing_pcts,
        target_column=target_col,
        target_distribution=target_dist,
        anomalies=anomalies,
    )


def _load_csv_file(path: Path) -> pd.DataFrame:
    """Internal helper to load a CSV file safely."""
    if not path.is_file():
        raise DatasetNotFoundError(f"Dataset file not found at: {path.resolve()}")
    try:
        # Load copy to guarantee raw data remains pristine
        df = pd.read_csv(path)
        return df.copy()
    except Exception as exc:
        raise MalformedDatasetError(f"Failed to read CSV at {path.resolve()}: {exc}") from exc


def load_heart_disease_data(
    filepath: Optional[Path | str] = None,
    validate: bool = True
) -> pd.DataFrame:
    """Loads and validates the UCI Heart Disease dataset.

    Args:
        filepath: Optional path to the CSV file. Defaults to `Machine_Learning/datasets/raw/heart_disease_uci.csv`.
        validate: Whether to validate columns against expected schema.

    Returns:
        pd.DataFrame: Loaded copy of dataset.
    """
    path = Path(filepath) if filepath else (DEFAULT_RAW_DATA_DIR / "heart_disease_uci.csv")
    df = _load_csv_file(path)

    if validate:
        missing_cols = set(HEART_DISEASE_UCI_COLUMNS) - set(df.columns)
        if missing_cols:
            raise DatasetValidationError(
                f"Heart Disease UCI dataset missing expected columns: {sorted(missing_cols)}"
            )

    logger.info("Loaded Heart Disease UCI dataset: shape=%s from %s", df.shape, path)
    return df


def load_heart_failure_data(
    filepath: Optional[Path | str] = None,
    validate: bool = True
) -> pd.DataFrame:
    """Loads and validates the Heart Failure Clinical Records dataset.

    Args:
        filepath: Optional path to the CSV file. Defaults to `Machine_Learning/datasets/raw/heart_failure.csv`.
        validate: Whether to validate columns against expected schema.

    Returns:
        pd.DataFrame: Loaded copy of dataset.
    """
    path = Path(filepath) if filepath else (DEFAULT_RAW_DATA_DIR / "heart_failure.csv")
    df = _load_csv_file(path)

    if validate:
        missing_cols = set(HEART_FAILURE_COLUMNS) - set(df.columns)
        if missing_cols:
            raise DatasetValidationError(
                f"Heart Failure dataset missing expected columns: {sorted(missing_cols)}"
            )

    logger.info("Loaded Heart Failure dataset: shape=%s from %s", df.shape, path)
    return df


def load_arrhythmia_data(
    filepath: Optional[Path | str] = None,
    validate: bool = True
) -> pd.DataFrame:
    """Loads and validates the Arrhythmia Conditions dataset.

    Args:
        filepath: Optional path to the CSV file. Defaults to `Machine_Learning/datasets/raw/arrhythmia_conditions.csv`.
        validate: Whether to validate columns against expected schema.

    Returns:
        pd.DataFrame: Loaded copy of dataset.
    """
    path = Path(filepath) if filepath else (DEFAULT_RAW_DATA_DIR / "arrhythmia_conditions.csv")
    df = _load_csv_file(path)

    if validate:
        if "condition_group" not in df.columns:
            raise DatasetValidationError("Arrhythmia dataset missing target column 'condition_group'")
        if df.shape[1] != 280:
            raise DatasetValidationError(f"Arrhythmia dataset expected 280 columns, found {df.shape[1]}")

    logger.info("Loaded Arrhythmia dataset: shape=%s from %s", df.shape, path)
    return df


def load_dataset(
    dataset_name: str,
    filepath: Optional[Path | str] = None,
    validate: bool = True
) -> pd.DataFrame:
    """Unified loader dispatching by dataset name.

    Args:
        dataset_name: One of 'heart_disease_uci', 'heart_failure', 'arrhythmia_conditions'.
        filepath: Optional custom file path.
        validate: Whether to validate schema.

    Returns:
        pd.DataFrame: Loaded dataset copy.
    """
    name = dataset_name.lower().strip()
    if name in ("heart_disease", "heart_disease_uci", "uci"):
        return load_heart_disease_data(filepath=filepath, validate=validate)
    elif name in ("heart_failure", "hf"):
        return load_heart_failure_data(filepath=filepath, validate=validate)
    elif name in ("arrhythmia", "arrhythmia_conditions"):
        return load_arrhythmia_data(filepath=filepath, validate=validate)
    else:
        raise ValueError(
            f"Unknown dataset name '{dataset_name}'. "
            f"Supported names: 'heart_disease_uci', 'heart_failure', 'arrhythmia_conditions'"
        )


def audit_all_datasets(raw_dir: Optional[Path | str] = None) -> Dict[str, DatasetAuditReport]:
    """Runs a complete audit across all three datasets and returns their reports."""
    base = Path(raw_dir) if raw_dir else DEFAULT_RAW_DATA_DIR

    df_hd = load_heart_disease_data(base / "heart_disease_uci.csv")
    df_hf = load_heart_failure_data(base / "heart_failure.csv")
    df_arr = load_arrhythmia_data(base / "arrhythmia_conditions.csv")

    return {
        "heart_disease_uci": audit_dataframe(
            df_hd, "heart_disease_uci", str(base / "heart_disease_uci.csv"), target_col="num"
        ),
        "heart_failure": audit_dataframe(
            df_hf, "heart_failure", str(base / "heart_failure.csv"), target_col="DEATH_EVENT"
        ),
        "arrhythmia_conditions": audit_dataframe(
            df_arr, "arrhythmia_conditions", str(base / "arrhythmia_conditions.csv"), target_col="condition_group"
        ),
    }


if __name__ == "__main__":
    reports = audit_all_datasets()
    for name, rep in reports.items():
        print(f"\n{'=' * 60}\nAUDIT REPORT: {name.upper()}\n{'=' * 60}")
        print(f"File: {rep.file_path}")
        print(f"Shape: {rep.row_count} rows x {rep.column_count} columns")
        print(f"Duplicates: {rep.duplicate_rows}")
        print(f"Target Column: {rep.target_column}")
        print(f"Target Distribution: {rep.target_distribution}")
        print(f"Missing Values: {rep.missing_values}")
        print(f"Anomalies & Clinical Notes: {rep.anomalies}")
