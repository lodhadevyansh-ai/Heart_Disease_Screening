# Machine Learning Architecture & Clinical Safety Guardrails

**Project**: Heart Disease Screening and Condition-Risk Prediction System  
**Document**: Machine Learning Architecture, Preprocessing Pipelines, Calibration & Safety  
**Classification**: Research & Educational Clinical Decision-Support Prototype  
**Date**: October 2026  

---

## 1. Machine Learning Strategy & Clinical Scope

In cardiovascular decision support, machine learning models frequently suffer from two critical hazards:
1. **Target Conflation**: Applying a model trained on hospitalized, diagnosed patients (e.g., heart failure follow-up mortality) to undifferentiated outpatients presenting with general symptoms (e.g., fatigue or leg swelling).
2. **False Reassurance**: Presenting an uncalibrated, low probability score to a clinician or patient that diminishes vigilance despite the presence of red-flag symptoms.

To prevent these hazards, the system adopts an architecture characterized by **clinical task gating**, **transparent target definitions**, **calibrated probability outputs**, and **strict rejection of unvalidated screening formulations**.

---

## 2. Supported Task Catalog & Model Specifications

The system supports three distinct machine learning tasks, each with explicit clinical cohorts and input requirements:

| Task Identifier | Clinical Cohort & Provenance | Algorithmic Pipeline | Target Definition | Score Representation | Outpatient Feasibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`coronary_artery_disease`** | Multi-center UCI Heart Disease cohort (Cleveland, Hungary, Long Beach, Switzerland; N=920) | Preprocessor (Median/MostFrequent Imputer + StandardScaler + OneHotEncoder) + Support Vector Classifier (RBF kernel, Platt scaled) | Angiographically documented CAD ($\ge 50\%$ diameter stenosis in major coronary vessels; `num > 0`) | **Calibrated Probability** ($0.0 \le P \le 1.0$), Brier Score: 0.1273, ECE: 0.0541 | **High**: Primary features (age, sex, chest pain type, resting BP, cholesterol, fasting glucose, resting ECG) align with standard clinical intake. |
| **`heart_failure_mortality`** | Hospitalized heart failure cohort (Faisalabad Institute of Cardiology, Pakistan; N=299, NYHA III-IV) | Preprocessor (StandardScaler + SimpleImputer) + Shallow Gradient Boosting Classifier | All-cause mortality during clinical follow-up among confirmed heart failure patients (`DEATH_EVENT = 1`) | **Classifier Confidence Score** ($0.0 \le S \le 1.0$), Brier Score: 0.1983, ECE: 0.1142. Explicitly flagged as *uncalibrated*. | **Constrained**: Restricted to risk-stratifying *diagnosed* heart failure patients. `time` (follow-up duration) is strictly excluded to prevent look-ahead bias. |
| **`arrhythmia_ecg`** | UCI Arrhythmia Database (N=430) | Preprocessor (VarianceThreshold + MedianImputer + RobustScaler) + Balanced Random Forest (Depth 6) | Multiclass classification into 5 electrophysiological condition groups (Normal, Ischemic Changes, Old MI, Conduction Blocks, Arrhythmias) | **Multiclass Probability Vector** (Raw forest vote fractions) | **Conditional**: Requires precomputed quantitative 12-lead ECG features (intervals, deflections). Patient-reported symptoms alone cannot be used. |

---

## 3. Explicit Rejection of Unsupported Tasks

The ML inference dispatcher rejects clinically invalid tasks by design:

1. **`heart_failure_screening` (REJECTED with HTTP 400)**:
   - *Rationale*: Outpatient heart failure screening requires clinical history, physical examination (elevated jugular venous pressure, pulmonary rales), biomarkers (BNP/NT-proBNP), and echocardiographic ejection fraction. The Ahmad et al. dataset measures follow-up survival among patients *already diagnosed* with severe heart failure, not disease onset. Applying this model to screen healthy individuals is scientifically invalid.
2. **Arrhythmia Classification from Symptoms Alone (REJECTED with HTTP 400)**:
   - *Rationale*: Symptoms such as palpitations or lightheadedness are non-specific and cannot substitute for 12-lead electrocardiographic deflections. Inference without ECG quantitative features is strictly refused.

---

## 4. Preprocessing Pipelines & Leakage Prevention

### 4.1. Imputation Strategy
- **Training-Set-Only Fitting**: All imputers, scalers, and encoders are fit strictly on training splits. Test and inference data are transformed using stored training parameters to eliminate data leakage.
- **Physiological Zero Replacement**:
  - Serum cholesterol (`chol == 0`) and resting blood pressure (`trestbps == 0`) are treated as missing values (`NaN`) and imputed via training set median.
- **Zero Silent Imputation During Inference**:
  - The inference engine requires all necessary predictors to be explicitly provided. If an essential feature is absent, the API returns HTTP 422 with the exact missing fields instead of silently imputing zero or population means.

### 4.2. Target Leakage Prevention in Heart Failure Modeling
- In the raw Ahmad et al. heart failure dataset, the feature `time` represents the number of days the patient was followed before death or administrative censoring.
- Including `time` creates severe look-ahead leakage, because patients who died early have small `time` values by definition, while survivors have large values.
- **Architectural Control**: The `time` variable is stripped from the feature matrix prior to model training and prospective inference.

---

## 5. Probability Calibration & Diagnostic Metrics

A raw classifier score (such as an SVM margin or uncalibrated decision tree leaf proportion) does not equal the empirical probability of disease. In clinical decision support, poorly calibrated scores mislead risk communication.

### 5.1. Calibration Methods
- **Platt Scaling**: Logistic regression fitted via cross-validation on classifier decision values (`SVC(probability=True)`).
- **Expected Calibration Error (ECE)**:
  $$\text{ECE} = \sum_{m=1}^{M} \frac{|B_m|}{N} |\text{acc}(B_m) - \text{conf}(B_m)|$$
  where predictions are grouped into $M=10$ confidence bins $B_m$.

### 5.2. Measured Calibration Results
- **Coronary Artery Disease Model**:
  - Calibration: Well-calibrated via Platt scaling.
  - Brier Score: **0.1273**
  - ECE: **0.0541** (5.4% mean discrepancy between predicted probability and observed frequency).
- **Heart Failure Mortality Model**:
  - Calibration: Moderately calibrated raw score.
  - Brier Score: **0.1983**
  - ECE: **0.1142**
  - Clinical Guardrail: Output is explicitly labeled as a *classifier confidence score*, accompanied by wide confidence interval warnings.

---

## 6. Model Explainability & Interpretability

1. **SHAP (SHapley Additive exPlanations)**:
   - TreeExplainer is utilized for tree-based models (Random Forest, Gradient Boosting).
   - Linear / Kernel explainer approximations are utilized for linear and kernel models.
   - For every prediction, the top positive and negative contributing clinical features are computed and returned as structured attributions.
2. **Mandatory Educational Disclaimer**:
   - Every explanation payload includes a standardized disclaimer:  
     *"Feature attributions reflect statistical associations within the training cohort and do not establish direct individual clinical causation. Clinical correlation by an attending physician is required."*

---

## 7. Model Artifact Integrity & Registry

Model pipelines and metadata are stored under version-controlled directories:

```
Machine_Learning/
├── artifacts/
│   ├── cad_model.joblib
│   ├── heart_failure_mortality_model.joblib
│   └── arrhythmia_model.joblib
├── model_metadata/
│   ├── heart_disease.json
│   ├── heart_failure.json
│   ├── arrhythmia.json
│   ├── feature_schema.json
│   └── evaluation_metrics.json
```

Each artifact bundles:
- Preprocessing transformers (imputers, scalers, encoders).
- Estimator object.
- Model hyperparameters, training date, commit hash, and target definition.
- Expected feature names and validation boundaries.
