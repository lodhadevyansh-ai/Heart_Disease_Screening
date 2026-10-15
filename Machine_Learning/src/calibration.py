"""
Probability calibration evaluation and adjustment for clinical ML models.

This module provides tools to assess calibration (Brier score, Expected Calibration Error,
reliability curves) and fit probability calibrators (e.g., Platt scaling / Sigmoid) on
validation splits separate from the held-out test data.

Clinical Disclaimer:
A model with high discrimination (ROC-AUC) may still be poorly calibrated.
Probabilities should only be interpreted as clinical risk likelihoods when
empirical calibration has been rigorously demonstrated.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.metrics import brier_score_loss


def compute_expected_calibration_error(
    y_true: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
    n_bins: int = 10,
    strategy: str = "uniform",
) -> float:
    """
    Compute Expected Calibration Error (ECE).
    
    ECE measures the weighted average difference between predicted confidence
    and empirical accuracy across probability bins.
    
    Parameters
    ----------
    y_true : array-like of shape (n_samples,)
        True binary labels (0 or 1).
    y_prob : array-like of shape (n_samples,)
        Predicted probabilities for the positive class.
    n_bins : int, default=10
        Number of bins.
    strategy : {'uniform', 'quantile'}, default='uniform'
        Binning strategy.
        
    Returns
    -------
    float
        Expected Calibration Error in [0, 1].
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)
    
    if len(y_true_arr) == 0:
        return 0.0
        
    if strategy == "uniform":
        bins = np.linspace(0.0, 1.0, n_bins + 1)
    elif strategy == "quantile":
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bins = np.percentile(y_prob_arr, quantiles * 100)
        bins[0] = 0.0
        bins[-1] = 1.0
        bins = np.unique(bins)
    else:
        raise ValueError(f"Unknown binning strategy: {strategy}")

    bin_assignments = np.digitize(y_prob_arr, bins) - 1
    # Clip to valid range [0, len(bins) - 2]
    bin_assignments = np.clip(bin_assignments, 0, len(bins) - 2)

    total_samples = len(y_true_arr)
    ece = 0.0

    for i in range(len(bins) - 1):
        idx = bin_assignments == i
        bin_count = np.sum(idx)
        if bin_count > 0:
            bin_acc = np.mean(y_true_arr[idx])
            bin_conf = np.mean(y_prob_arr[idx])
            ece += (bin_count / total_samples) * np.abs(bin_acc - bin_conf)

    return float(ece)


def compute_calibration_diagnostics(
    y_true: Union[np.ndarray, List[int]],
    y_prob: Union[np.ndarray, List[float]],
    n_bins: int = 10,
    strategy: str = "uniform",
) -> Dict[str, Any]:
    """
    Compute comprehensive calibration metrics and reliability curve points.
    
    Parameters
    ----------
    y_true : array-like
        Ground truth binary labels (0 or 1).
    y_prob : array-like
        Predicted positive class probabilities in [0, 1].
    n_bins : int
        Number of calibration bins.
    strategy : str
        'uniform' or 'quantile'.
        
    Returns
    -------
    dict
        Calibration diagnostics including Brier score, ECE, maximum calibration error,
        fraction of positives, and mean predicted values.
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_prob_arr = np.asarray(y_prob).astype(float)

    brier = float(brier_score_loss(y_true_arr, y_prob_arr))
    ece = compute_expected_calibration_error(y_true_arr, y_prob_arr, n_bins=n_bins, strategy=strategy)

    try:
        prob_true, prob_pred = calibration_curve(
            y_true_arr, y_prob_arr, n_bins=n_bins, strategy=strategy
        )
        prob_true_list = [float(v) for v in prob_true]
        prob_pred_list = [float(v) for v in prob_pred]
        mce = float(np.max(np.abs(prob_true - prob_pred))) if len(prob_true) > 0 else 0.0
    except Exception:
        prob_true_list = []
        prob_pred_list = []
        mce = 0.0

    # Qualitative calibration assessment
    if brier < 0.15 and ece < 0.08:
        quality = "well_calibrated"
    elif brier < 0.22 and ece < 0.15:
        quality = "moderately_calibrated"
    else:
        quality = "poorly_calibrated"

    return {
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "maximum_calibration_error": round(mce, 4),
        "calibration_quality": quality,
        "n_samples": len(y_true_arr),
        "n_bins": n_bins,
        "reliability_curve": {
            "fraction_of_positives": [round(x, 4) for x in prob_true_list],
            "mean_predicted_probability": [round(x, 4) for x in prob_pred_list],
        },
        "caution": (
            "Calibration evaluated on validation split. Interpret probabilities with "
            "caution in clinical decision support."
        ),
    }


def fit_calibrated_pipeline(
    trained_pipeline: Any,
    X_val: Union[pd.DataFrame, np.ndarray],
    y_val: Union[pd.Series, np.ndarray],
    method: str = "sigmoid",
) -> Tuple[CalibratedClassifierCV, Dict[str, Any]]:
    """
    Fit a probability calibrator on validation data separate from the training
    and final test sets.
    
    Parameters
    ----------
    trained_pipeline : sklearn.pipeline.Pipeline or classifier
        Fitted pipeline or estimator with predict_proba or decision_function.
    X_val : DataFrame or ndarray
        Held-out validation features.
    y_val : Series or ndarray
        Held-out validation labels.
    method : {'sigmoid', 'isotonic'}, default='sigmoid'
        'sigmoid' (Platt scaling) is strongly recommended for cohorts with N < 1000
        to prevent severe overfitting seen with isotonic regression.
        
    Returns
    -------
    calibrated_clf : CalibratedClassifierCV
        Calibrated model ready for probability inference.
    diagnostics : dict
        Pre- and post-calibration diagnostics on the validation split.
    """
    y_val_arr = np.asarray(y_val)
    
    # Check sample size safety
    n_samples = len(y_val_arr)
    if n_samples < 50 and method == "isotonic":
        # Force fallback to sigmoid to prevent rank degeneration
        method = "sigmoid"

    # Pre-calibration diagnostics
    if hasattr(trained_pipeline, "predict_proba"):
        pre_probs = trained_pipeline.predict_proba(X_val)
        if pre_probs.ndim == 2 and pre_probs.shape[1] == 2:
            pre_pos_prob = pre_probs[:, 1]
            pre_diag = compute_calibration_diagnostics(y_val_arr, pre_pos_prob)
        else:
            pre_diag = {"note": "Multiclass or non-standard probability shape"}
    else:
        pre_diag = {"note": "Base estimator lacks predict_proba"}

    # Fit calibrator on validation set using cv='prefit'
    calibrated_clf = CalibratedClassifierCV(
        estimator=trained_pipeline,
        method=method,
        cv="prefit",
    )
    calibrated_clf.fit(X_val, y_val_arr)

    # Post-calibration diagnostics
    post_probs = calibrated_clf.predict_proba(X_val)
    if post_probs.ndim == 2 and post_probs.shape[1] == 2:
        post_pos_prob = post_probs[:, 1]
        post_diag = compute_calibration_diagnostics(y_val_arr, post_pos_prob)
    else:
        post_diag = {"note": "Multiclass or non-standard probability shape"}

    diagnostics = {
        "method": method,
        "validation_samples": n_samples,
        "pre_calibration": pre_diag,
        "post_calibration": post_diag,
    }

    return calibrated_clf, diagnostics
