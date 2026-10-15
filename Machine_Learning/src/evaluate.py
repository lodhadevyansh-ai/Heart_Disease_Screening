"""Evaluation Metrics Module for Clinical Decision-Support Models.

Provides standardized, mathematically rigorous evaluation routines for binary
and multi-class cardiovascular risk prediction models.
All metrics are returned as native JSON-serializable types.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


def evaluate_binary_classifier(
    y_true: Union[np.ndarray, List[int]],
    y_pred: Union[np.ndarray, List[int]],
    y_prob: Optional[Union[np.ndarray, List[float]]] = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Calculates comprehensive binary classification performance metrics.

    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_pred: Predicted discrete labels (0 or 1).
        y_prob: Predicted positive-class probabilities [0.0, 1.0].
        threshold: Decision threshold used for classification.

    Returns:
        Dict[str, Any]: Dictionary of evaluation metrics.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_pred_arr = np.asarray(y_pred, dtype=int)

    # Basic metrics
    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    balanced_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    precision = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    recall = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # Confusion matrix: TN, FP, FN, TP
    cm = confusion_matrix(y_true_arr, y_pred_arr)
    tn, fp, fn, tp = (int(val) for val in cm.ravel())

    # Specificity: TN / (TN + FP)
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    # Negative Predictive Value (NPV): TN / (TN + FN)
    npv = float(tn / (tn + fn)) if (tn + fn) > 0 else 0.0

    results: Dict[str, Any] = {
        "sample_count": int(len(y_true_arr)),
        "decision_threshold": float(threshold),
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "precision": round(precision, 4),
        "recall_sensitivity": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1_score": round(f1, 4),
        "negative_predictive_value": round(npv, 4),
        "confusion_matrix": {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "matrix": cm.tolist(),
        },
    }

    # Probability-based metrics
    if y_prob is not None:
        y_prob_arr = np.asarray(y_prob, dtype=float)
        # Handle 2D probability array (n_samples, 2)
        if y_prob_arr.ndim == 2 and y_prob_arr.shape[1] == 2:
            y_prob_arr = y_prob_arr[:, 1]

        try:
            roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
            results["roc_auc"] = round(roc_auc, 4)
        except ValueError as err:
            logger.warning("Could not calculate ROC-AUC: %s", err)
            results["roc_auc"] = None

        try:
            # PR-AUC via precision_recall_curve and trapezoidal rule
            prec_arr, rec_arr, _ = precision_recall_curve(y_true_arr, y_prob_arr)
            pr_auc = float(np.trapezoid(prec_arr, rec_arr)) if hasattr(np, "trapezoid") else float(np.trapz(prec_arr, rec_arr))
            results["pr_auc"] = round(abs(pr_auc), 4)
        except Exception as err:
            logger.warning("Could not calculate PR-AUC: %s", err)
            results["pr_auc"] = None

        try:
            brier = float(brier_score_loss(y_true_arr, y_prob_arr))
            results["brier_score"] = round(brier, 4)
        except Exception:
            results["brier_score"] = None

    return results


def print_evaluation_summary(metrics: Dict[str, Any], model_name: str = "Model") -> None:
    """Prints a clear, formatted clinical evaluation summary."""
    print(f"\n{'=' * 60}")
    print(f"EVALUATION SUMMARY: {model_name}")
    print(f"{'=' * 60}")
    print(f"Sample Count       : {metrics.get('sample_count')}")
    print(f"Accuracy           : {metrics.get('accuracy'):.4f}")
    print(f"Balanced Accuracy  : {metrics.get('balanced_accuracy'):.4f}")
    print(f"Sensitivity/Recall : {metrics.get('recall_sensitivity'):.4f}")
    print(f"Specificity        : {metrics.get('specificity'):.4f}")
    print(f"Precision          : {metrics.get('precision'):.4f}")
    print(f"F1 Score           : {metrics.get('f1_score'):.4f}")
    if "roc_auc" in metrics and metrics["roc_auc"] is not None:
        print(f"ROC-AUC            : {metrics.get('roc_auc'):.4f}")
    if "pr_auc" in metrics and metrics["pr_auc"] is not None:
        print(f"PR-AUC             : {metrics.get('pr_auc'):.4f}")
    if "brier_score" in metrics and metrics["brier_score"] is not None:
        print(f"Brier Score        : {metrics.get('brier_score'):.4f}")

    cm = metrics.get("confusion_matrix", {})
    print(f"\nConfusion Matrix:")
    print(f"  TN: {cm.get('true_negatives'):<5} FP: {cm.get('false_positives'):<5}")
    print(f"  FN: {cm.get('false_negatives'):<5} TP: {cm.get('true_positives'):<5}")
    print(f"{'=' * 60}\n")


def evaluate_multiclass_classifier(
    y_true: Union[np.ndarray, List[Any]],
    y_pred: Union[np.ndarray, List[Any]],
    y_prob: Optional[Union[np.ndarray, List[Any]]] = None,
    class_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculates comprehensive multiclass classification metrics with per-class and macro reporting.

    Args:
        y_true: Ground truth target classes.
        y_pred: Predicted target classes.
        y_prob: Predicted probability array of shape (n_samples, n_classes).
        class_labels: Ordered list of class label names.

    Returns:
        Dict[str, Any]: Structured evaluation metrics.
    """
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)

    unique_labels = class_labels if class_labels is not None else sorted(list(np.unique(np.concatenate([y_true_arr, y_pred_arr]))))

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    balanced_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    macro_prec = float(precision_score(y_true_arr, y_pred_arr, labels=unique_labels, average="macro", zero_division=0))
    macro_rec = float(recall_score(y_true_arr, y_pred_arr, labels=unique_labels, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true_arr, y_pred_arr, labels=unique_labels, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true_arr, y_pred_arr, labels=unique_labels, average="weighted", zero_division=0))

    # Per-class metrics
    p_per_class, r_per_class, f_per_class, s_per_class = precision_recall_fscore_support(
        y_true_arr, y_pred_arr, labels=unique_labels, zero_division=0
    )

    per_class_dict = {}
    for i, label in enumerate(unique_labels):
        per_class_dict[str(label)] = {
            "precision": round(float(p_per_class[i]), 4),
            "recall": round(float(r_per_class[i]), 4),
            "f1_score": round(float(f_per_class[i]), 4),
            "support": int(s_per_class[i]),
        }

    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=unique_labels)

    results: Dict[str, Any] = {
        "sample_count": int(len(y_true_arr)),
        "class_count": len(unique_labels),
        "class_labels": [str(c) for c in unique_labels],
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(balanced_acc, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class_metrics": per_class_dict,
        "confusion_matrix": cm.tolist(),
    }

    # OvR Multi-class ROC-AUC if probabilities are available
    if y_prob is not None:
        y_prob_arr = np.asarray(y_prob, dtype=float)
        try:
            roc_auc_ovr = float(roc_auc_score(y_true_arr, y_prob_arr, multi_class="ovr", average="macro", labels=unique_labels))
            results["macro_roc_auc_ovr"] = round(roc_auc_ovr, 4)
        except Exception as err:
            logger.warning("Could not calculate multiclass ROC-AUC: %s", err)
            results["macro_roc_auc_ovr"] = None

    return results


def print_multiclass_summary(metrics: Dict[str, Any], model_name: str = "Multiclass Model") -> None:
    """Prints formatted multiclass evaluation metrics."""
    print(f"\n{'=' * 65}")
    print(f"MULTICLASS EVALUATION SUMMARY: {model_name}")
    print(f"{'=' * 65}")
    print(f"Sample Count       : {metrics.get('sample_count')}")
    print(f"Overall Accuracy   : {metrics.get('accuracy'):.4f}")
    print(f"Balanced Accuracy  : {metrics.get('balanced_accuracy'):.4f}")
    print(f"Macro Precision    : {metrics.get('macro_precision'):.4f}")
    print(f"Macro Recall       : {metrics.get('macro_recall'):.4f}")
    print(f"Macro F1 Score     : {metrics.get('macro_f1'):.4f}")
    print(f"Weighted F1 Score  : {metrics.get('weighted_f1'):.4f}")
    if "macro_roc_auc_ovr" in metrics and metrics["macro_roc_auc_ovr"] is not None:
        print(f"Macro ROC-AUC (OvR): {metrics.get('macro_roc_auc_ovr'):.4f}")

    print(f"\nPer-Class Breakdown:")
    per_class = metrics.get("per_class_metrics", {})
    for label, stats in per_class.items():
        print(
            f"  {label:<30}: Recall={stats['recall']:.4f}, Prec={stats['precision']:.4f}, F1={stats['f1_score']:.4f} (N={stats['support']})"
        )
    print(f"{'=' * 65}\n")

