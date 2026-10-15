"""
Model Explainability and Feature Attribution Module.

Provides local (patient-level) and global (cohort-level) feature attributions
for clinical machine learning models, supporting TreeExplainer (SHAP) and
robust local perturbation attribution with non-causal clinical guardrails.

CRITICAL CLINICAL DIRECTIVE:
Feature attributions demonstrate statistical associations within a specific
retrospective training distribution and model architecture. They DO NOT
indicate physiological causation, disease etiology, or validated clinical
treatment targets.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

# Mandatory non-causal disclaimer constant
CAUSAL_DISCLAIMER = (
    "Feature attributions indicate statistical associations within the retrospective "
    "training dataset and model architecture. They DO NOT represent causal mechanisms, "
    "pathophysiological proof, or clinical treatment targets."
)


def get_feature_names_from_pipeline(pipeline: Pipeline, raw_input_df: pd.DataFrame) -> List[str]:
    """
    Extract transformed feature names from a fitted scikit-learn Pipeline.
    
    Parameters
    ----------
    pipeline : Pipeline
        Fitted scikit-learn Pipeline.
    raw_input_df : pd.DataFrame
        Raw input DataFrame representing input schema.
        
    Returns
    -------
    list of str
        Names of transformed features fed into the final classifier.
    """
    # Check if pipeline has a preprocessor step
    preprocessor = None
    for step_name, step in pipeline.steps[:-1]:
        if hasattr(step, "get_feature_names_out"):
            preprocessor = step

    if preprocessor is not None and hasattr(preprocessor, "get_feature_names_out"):
        try:
            raw_names = preprocessor.get_feature_names_out()
            # Clean up sklearn prefix prefixes (e.g. 'num__', 'cat__')
            clean_names = []
            for name in raw_names:
                parts = name.split("__")
                clean_names.append(parts[-1] if len(parts) > 1 else name)
            return clean_names
        except Exception:
            pass

    # Transform a single row to inspect dimensionality
    try:
        transformer_steps = pipeline.steps[:-1]
        X_trans = raw_input_df.copy()
        for _, step in transformer_steps:
            if hasattr(step, "transform"):
                X_trans = step.transform(X_trans)
        n_features = X_trans.shape[1] if hasattr(X_trans, "shape") else len(raw_input_df.columns)
        return [f"feature_{i}" for i in range(n_features)]
    except Exception:
        return list(raw_input_df.columns)


def explain_prediction_local(
    pipeline: Pipeline,
    input_df: pd.DataFrame,
    top_k: int = 5,
    target_class_index: int = 1,
    background_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute local (patient-level) feature attributions for a single clinical input.
    
    Uses SHAP TreeExplainer for tree-based models where feasible, with a robust
    deterministic marginal perturbation fallback for kernel / non-tree estimators
    (e.g., SVC RBF) to guarantee sub-second latency for API requests.
    
    Parameters
    ----------
    pipeline : Pipeline
        Fitted scikit-learn Pipeline.
    input_df : pd.DataFrame
        Single-row (or multi-row) DataFrame of patient inputs.
    top_k : int, default=5
        Number of top positive and negative features to extract.
    target_class_index : int, default=1
        Target class index (1 for binary positive class).
    background_df : pd.DataFrame, optional
        Background reference cohort.
        
    Returns
    -------
    dict
        Structured local explanation dictionary with attributions, top drivers,
        and the mandatory non-causal clinical disclaimer.
    """
    if not isinstance(input_df, pd.DataFrame):
        raise TypeError("input_df must be a pandas DataFrame")

    single_row = input_df.iloc[[0]].copy()
    classifier = pipeline.steps[-1][1]
    feature_names = get_feature_names_from_pipeline(pipeline, single_row)

    # Transform input through preprocessing steps
    transformer_steps = pipeline.steps[:-1]
    X_trans = single_row.copy()
    for _, step in transformer_steps:
        if hasattr(step, "transform"):
            X_trans = step.transform(X_trans)

    if hasattr(X_trans, "toarray"):
        X_trans_arr = X_trans.toarray()
    else:
        X_trans_arr = np.asarray(X_trans)

    method_used = "unknown"
    attributions: Dict[str, float] = {}
    baseline_val = 0.5

    # Strategy 1: TreeExplainer for Tree Ensembles (RandomForest, GradientBoosting)
    is_tree_model = any(
        cls_name in type(classifier).__name__
        for cls_name in ["RandomForest", "GradientBoosting", "DecisionTree", "ExtraTrees"]
    )

    if is_tree_model:
        try:
            import shap  # type: ignore[import-untyped, import-not-found]
            explainer = shap.TreeExplainer(classifier)
            shap_values = explainer.shap_values(X_trans_arr)

            # Handle shap_values shape across versions and model types
            if isinstance(shap_values, list):
                # Binary or multiclass list of arrays
                class_shap = shap_values[min(target_class_index, len(shap_values) - 1)][0]
            elif hasattr(shap_values, "ndim") and shap_values.ndim == 3:
                # Shape: (n_samples, n_features, n_classes)
                class_shap = shap_values[0, :, min(target_class_index, shap_values.shape[2] - 1)]
            else:
                # 2D array (n_samples, n_features)
                class_shap = shap_values[0]

            if hasattr(explainer.expected_value, "__len__"):
                baseline_val = float(explainer.expected_value[min(target_class_index, len(explainer.expected_value) - 1)])
            else:
                baseline_val = float(explainer.expected_value)

            method_used = "shap_tree_explainer"
            for i, name in enumerate(feature_names[: len(class_shap)]):
                attributions[name] = round(float(class_shap[i]), 5)

        except Exception:
            # Fall back to perturbation if SHAP fails or crashes
            method_used = "fallback_perturbation"

    # Strategy 2: Deterministic Feature Attribution (for SVC RBF or fallback)
    if not attributions:
        method_used = "marginal_perturbation_attribution"
        # Base probability of the unperturbed sample
        if hasattr(pipeline, "predict_proba"):
            base_prob = float(pipeline.predict_proba(single_row)[0, min(target_class_index, 1)])
        else:
            base_prob = 0.5
        baseline_val = base_prob

        # Perturb each transformed feature by its standardized delta and compute difference
        sample_vec = X_trans_arr[0].copy()
        for i in range(len(sample_vec)):
            fname = feature_names[i] if i < len(feature_names) else f"feature_{i}"
            val = sample_vec[i]
            
            # Compare to neutral zero (scaled mean)
            perturbed_vec = sample_vec.copy()
            perturbed_vec[i] = 0.0  # Zero out normalized deviation
            
            if hasattr(classifier, "predict_proba"):
                try:
                    prob_perturbed = float(classifier.predict_proba([perturbed_vec])[0, min(target_class_index, 1)])
                    delta = base_prob - prob_perturbed
                except Exception:
                    delta = 0.0
            elif hasattr(classifier, "decision_function"):
                try:
                    score_orig = float(classifier.decision_function([sample_vec])[0])
                    score_pert = float(classifier.decision_function([perturbed_vec])[0])
                    delta = score_orig - score_pert
                except Exception:
                    delta = 0.0
            else:
                delta = 0.0

            attributions[fname] = round(float(delta), 5)

    # Sort positive (risk-increasing) and negative (risk-decreasing) features
    sorted_features = sorted(attributions.items(), key=lambda x: x[1], reverse=True)
    
    top_positive = [
        {"feature": k, "attribution": v, "direction": "increases_predicted_risk"}
        for k, v in sorted_features if v > 0.0001
    ][:top_k]

    top_negative = [
        {"feature": k, "attribution": v, "direction": "decreases_predicted_risk"}
        for k, v in reversed(sorted_features) if v < -0.0001
    ][:top_k]

    return {
        "status": "success",
        "method": method_used,
        "baseline_value": round(baseline_val, 4),
        "target_class_index": target_class_index,
        "top_risk_increasing_features": top_positive,
        "top_risk_decreasing_features": top_negative,
        "all_attributions": attributions,
        "non_causal_disclaimer": CAUSAL_DISCLAIMER,
    }


def compute_cohort_feature_importance(
    pipeline: Pipeline,
    X_val: pd.DataFrame,
    y_val: Union[pd.Series, np.ndarray],
    n_repeats: int = 5,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Compute cohort-level global feature importances via permutation importance
    evaluated on the held-out validation cohort.
    
    Parameters
    ----------
    pipeline : Pipeline
        Fitted scikit-learn Pipeline.
    X_val : pd.DataFrame
        Validation features.
    y_val : Series or ndarray
        Validation labels.
    n_repeats : int, default=5
        Number of permutation repeats.
    random_state : int, default=42
        Reproducibility seed.
        
    Returns
    -------
    dict
        Global feature importance metrics and ranking.
    """
    perm = permutation_importance(
        pipeline,
        X_val,
        y_val,
        n_repeats=n_repeats,
        random_state=random_state,
        scoring="roc_auc" if len(np.unique(y_val)) == 2 else "balanced_accuracy",
    )

    feature_names = list(X_val.columns)
    importances = {}
    for i, name in enumerate(feature_names):
        importances[name] = {
            "mean_importance": round(float(perm.importances_mean[i]), 5),
            "std_importance": round(float(perm.importances_std[i]), 5),
        }

    # Rank by mean importance
    ranked = sorted(importances.items(), key=lambda x: x[1]["mean_importance"], reverse=True)

    return {
        "scoring_metric": "roc_auc" if len(np.unique(y_val)) == 2 else "balanced_accuracy",
        "n_repeats": n_repeats,
        "ranked_features": [{"feature": k, **v} for k, v in ranked],
        "non_causal_disclaimer": CAUSAL_DISCLAIMER,
    }
