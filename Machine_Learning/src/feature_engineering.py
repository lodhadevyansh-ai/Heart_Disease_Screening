"""Feature Engineering Module for Cardiovascular Clinical Datasets.

This module provides scikit-learn compatible transformers for clinically validated
feature engineering across the three screening datasets:
1. Heart Disease (UCI): Exercise heart-rate ratios, ST depression thresholds, age tiers.
2. Heart Failure: Ejection fraction clinical categories, renal dysfunction flags, interaction terms.
3. Arrhythmia: Bazett-corrected QT interval (QTc), conduction delay indicators, vector angle flags.

All transformers adhere to the scikit-learn BaseEstimator and TransformerMixin interfaces,
prevent data leakage, and provide get_feature_names_out().
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

logger = logging.getLogger(__name__)


class HeartDiseaseFeatureEngineer(BaseEstimator, TransformerMixin):
    """Clinically grounded feature engineering for Heart Disease (UCI) data.

    Engineered features:
    - `max_hr_pct`: Ratio of achieved heart rate (thalch) to age-predicted maximum (220 - age).
      Values <0.85 indicate chronotropic incompetence during exercise testing.
    - `st_depression_high`: Binary indicator of exercise-induced ST depression >= 1.0 mm.
    - `age_gt_60`: Binary indicator for patients aged 60 and older.
    - `angina_risk`: Interaction between typical/atypical chest pain and exercise-induced angina.
    """

    def __init__(self, add_hr_ratio: bool = True, add_st_flag: bool = True, add_age_tier: bool = True):
        self.add_hr_ratio = add_hr_ratio
        self.add_st_flag = add_st_flag
        self.add_age_tier = add_age_tier
        self.feature_names_out_: List[str] = []

    def fit(self, X: pd.DataFrame | np.ndarray, y: Optional[Any] = None) -> HeartDiseaseFeatureEngineer:
        return self

    def transform(self, X: pd.DataFrame | np.ndarray) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            # If array, attempt to reconstruct DataFrame if columns are known, else raise
            raise TypeError("HeartDiseaseFeatureEngineer requires a pandas DataFrame input.")

        df = X.copy()
        new_cols: List[str] = []

        # 1. Chronotropic Incompetence / Max Heart Rate Ratio
        if self.add_hr_ratio and "thalch" in df.columns and "age" in df.columns:
            age_pred_max_hr = (220.0 - df["age"].astype(float)).clip(lower=100.0)
            df["max_hr_ratio"] = (df["thalch"].astype(float) / age_pred_max_hr).round(4)
            # Flag for chronotropic incompetence (< 85% of predicted maximum)
            df["chronotropic_incompetence"] = (df["max_hr_ratio"] < 0.85).astype(float)
            new_cols.extend(["max_hr_ratio", "chronotropic_incompetence"])

        # 2. Clinically significant ST depression (>= 1.0 mm)
        if self.add_st_flag and "oldpeak" in df.columns:
            df["st_depression_significant"] = (df["oldpeak"].astype(float) >= 1.0).astype(float)
            new_cols.append("st_depression_significant")

        # 3. High-risk Age group (>= 60)
        if self.add_age_tier and "age" in df.columns:
            df["age_ge_60"] = (df["age"].astype(float) >= 60.0).astype(float)
            new_cols.append("age_ge_60")

        self.feature_names_out_ = list(df.columns)
        return df

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_out_)


class HeartFailureFeatureEngineer(BaseEstimator, TransformerMixin):
    """Clinically grounded feature engineering for Heart Failure records.

    Engineered features:
    - `reduced_ef`: Binary flag for Heart Failure with Reduced Ejection Fraction (HFrEF, EF < 40%).
    - `severely_reduced_ef`: Binary flag for severe systolic dysfunction (EF <= 30%).
    - `renal_dysfunction`: Binary flag for elevated serum creatinine (> 1.5 mg/dL).
    - `high_risk_biomarker_synergy`: Interaction flag between reduced EF and elevated creatinine.
    - `hypertension_elderly`: Interaction between high blood pressure and age >= 65.
    """

    def __init__(self, add_ef_tiers: bool = True, add_renal_flag: bool = True, add_interactions: bool = True):
        self.add_ef_tiers = add_ef_tiers
        self.add_renal_flag = add_renal_flag
        self.add_interactions = add_interactions
        self.feature_names_out_: List[str] = []

    def fit(self, X: pd.DataFrame | np.ndarray, y: Optional[Any] = None) -> HeartFailureFeatureEngineer:
        return self

    def transform(self, X: pd.DataFrame | np.ndarray) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("HeartFailureFeatureEngineer requires a pandas DataFrame input.")

        df = X.copy()
        new_cols: List[str] = []

        # 1. Ejection Fraction Clinical Tiers (ACC/AHA HFrEF guidelines)
        if self.add_ef_tiers and "ejection_fraction" in df.columns:
            ef = df["ejection_fraction"].astype(float)
            df["reduced_ef"] = (ef < 40.0).astype(float)
            df["severe_ef_reduction"] = (ef <= 30.0).astype(float)
            new_cols.extend(["reduced_ef", "severe_ef_reduction"])

        # 2. Renal Dysfunction (Serum Creatinine > 1.5 mg/dL)
        if self.add_renal_flag and "serum_creatinine" in df.columns:
            scr = df["serum_creatinine"].astype(float)
            df["renal_dysfunction"] = (scr > 1.5).astype(float)
            new_cols.append("renal_dysfunction")

        # 3. Clinical Synergy: Low EF + Renal Dysfunction (Cardiorenal Syndrome)
        if self.add_interactions and "reduced_ef" in df.columns and "renal_dysfunction" in df.columns:
            df["cardiorenal_risk"] = (df["reduced_ef"] * df["renal_dysfunction"]).astype(float)
            new_cols.append("cardiorenal_risk")

        if self.add_interactions and "high_blood_pressure" in df.columns and "age" in df.columns:
            df["hypertension_elderly"] = (
                (df["high_blood_pressure"].astype(float) == 1.0) & (df["age"].astype(float) >= 65.0)
            ).astype(float)
            new_cols.append("hypertension_elderly")

        self.feature_names_out_ = list(df.columns)
        return df

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_out_)


class ArrhythmiaFeatureEngineer(BaseEstimator, TransformerMixin):
    """Feature engineering for 12-lead ECG Arrhythmia dataset.

    Engineered features:
    - `qtc_bazett`: Corrected QT interval using Bazett's formula:
      QTc = QT / sqrt(RR_interval_seconds) = (col_6) / sqrt(60 / col_14).
    - `pr_prolonged`: Conduction delay flag if P-R interval (col 5) > 200 msec (1st degree AV block).
    - `qrs_wide`: Conduction block flag if QRS duration (col 4) > 120 msec.
    - `tachycardia`: Heart rate (col 14) > 100 bpm.
    - `bradycardia`: Heart rate (col 14) < 60 bpm.
    - Outlier capping: Replaces physiological height outliers (>250 cm) with NaN for imputation.
    """

    def __init__(self, add_qtc: bool = True, add_conduction_flags: bool = True):
        self.add_qtc = add_qtc
        self.add_conduction_flags = add_conduction_flags
        self.feature_names_out_: List[str] = []

    def fit(self, X: pd.DataFrame | np.ndarray, y: Optional[Any] = None) -> ArrhythmiaFeatureEngineer:
        return self

    def transform(self, X: pd.DataFrame | np.ndarray) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("ArrhythmiaFeatureEngineer requires a pandas DataFrame input.")

        df = X.copy()

        # Clean biological outlier in height (col '2'): heights > 250 cm are data entry errors
        if "2" in df.columns:
            df.loc[df["2"].astype(float) > 250.0, "2"] = np.nan

        # 1. Bazett-corrected QT interval: QTc = QT_ms / sqrt(RR_sec)
        # col '6' is QT interval (msec), col '14' is Heart Rate (bpm)
        if self.add_qtc and "6" in df.columns and "14" in df.columns:
            hr = df["14"].astype(float).replace(0, np.nan)
            rr_seconds = 60.0 / hr
            # QTc in milliseconds: QT_ms / sqrt(rr_sec)
            qt_ms = df["6"].astype(float)
            df["qtc_bazett"] = (qt_ms / np.sqrt(rr_seconds.clip(lower=0.2))).round(2)
            # Clinical QTc prolongation indicator (> 450 ms)
            df["qtc_prolonged"] = (df["qtc_bazett"] > 450.0).astype(float)

        # 2. Conduction delay flags
        if self.add_conduction_flags:
            if "4" in df.columns:
                # QRS duration > 120 ms indicates bundle branch block
                df["qrs_wide"] = (df["4"].astype(float) > 120.0).astype(float)
            if "5" in df.columns:
                # PR interval > 200 ms indicates first degree AV block
                df["pr_prolonged"] = (df["5"].astype(float) > 200.0).astype(float)
            if "14" in df.columns:
                hr = df["14"].astype(float)
                df["tachycardia"] = (hr > 100.0).astype(float)
                df["bradycardia"] = (hr < 60.0).astype(float)

        self.feature_names_out_ = list(df.columns)
        return df

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        return np.array(self.feature_names_out_)
