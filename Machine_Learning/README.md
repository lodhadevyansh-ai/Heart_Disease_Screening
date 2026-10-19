# Machine Learning Subsystem & Pipelines

**Subsystem**: Machine Learning, Preprocessing, Calibration & Model Audit  
**Location**: `Machine_Learning/`  
**Classification**: Research & Educational Clinical Decision-Support Subsystem  

---

## 1. Subsystem Overview

The `Machine_Learning` directory contains the complete data science and predictive modeling pipeline for the Heart Disease Screening platform. The subsystem is structured into modular components:

```
Machine_Learning/
├── datasets/
│   ├── raw/                        # Immutably archived raw source CSVs
│   │   ├── heart_disease_uci.csv   # Cleveland & European multicenter CAD cohort
│   │   ├── heart_failure.csv       # Faisalabad hospitalized heart failure cohort
│   │   └── arrhythmia_conditions.csv # 12-lead ECG electrophysiology dataset
│   └── processed/                  # Cached, cleaned data splits
├── notebooks/                      # Exploratory & pipeline development notebooks
│   ├── 01_eda.ipynb                # Comprehensive dataset exploratory data analysis
│   ├── 02_heart_disease.ipynb      # CAD classifier training & Platt calibration
│   ├── 03_heart_failure.ipynb      # HF mortality model & leakage-free evaluation
│   └── 04_arrhythmia.ipynb         # Multiclass 12-lead ECG model development
├── src/                            # Production ML modules & dispatchers
│   ├── data_loader.py              # Schema validation and dataset ingestion
│   ├── feature_engineering.py      # Transformations, imputers, and encodings
│   ├── train.py                    # Training pipelines and hyperparameter tuning
│   ├── evaluate.py                 # Empirical calibration, Brier score, ROC/PR curves
│   ├── predict.py                  # Core inference logic with explicit feature mapping
│   ├── inference.py                # High-level task dispatch and error handling
│   └── calibration.py              # Platt scaling & Expected Calibration Error (ECE)
├── artifacts/                      # Serialized, reproducible model pipelines (.joblib)
│   ├── cad_model.joblib            # Calibrated Support Vector Classifier for CAD
│   ├── heart_failure_mortality_model.joblib # Gradient Boosting for HF mortality
│   └── arrhythmia_model.joblib     # Random Forest for 12-lead ECG condition grouping
└── model_metadata/                 # Schemas and recorded evaluation outputs
    ├── feature_schema.json         # Strict input bounds and data types
    ├── evaluation_metrics.json     # Measured empirical test metrics
    ├── heart_disease.json          # CAD model specifications and hyperparams
    ├── heart_failure.json          # HF model specifications and hyperparams
    └── arrhythmia.json             # Arrhythmia specifications and hyperparams
```

---

## 2. Models & Supported Tasks

### 2.1. Coronary Artery Disease Classifier (`coronary_artery_disease`)
- **Dataset**: UCI Heart Disease (`heart_disease_uci.csv`, N=920).
- **Target**: Binary CAD presence (`num > 0`, angiographic $\ge 50\%$ diameter stenosis).
- **Model**: Pipeline(StandardScaler + SimpleImputer(median) + OneHotEncoder) + Support Vector Classifier (RBF kernel, Platt scaling).
- **Output**: Calibrated Probability ($0.0 \le P \le 1.0$), Brier Score: 0.1273, ECE: 0.0541, ROC-AUC: 0.8985.
- **Input Features**: `age`, `sex`, `cp` (chest pain type), `trestbps`, `chol`, `fbs`, `restecg`, `thalach`, `exang`, `oldpeak`, `slope`, `ca`, `thal`.

### 2.2. Heart Failure Follow-up Mortality Risk (`heart_failure_mortality`)
- **Dataset**: Faisalabad Heart Failure Clinical Records (`heart_failure.csv`, N=299).
- **Target**: Follow-up all-cause mortality (`DEATH_EVENT = 1`) among diagnosed NYHA Class III-IV heart failure patients.
- **Model**: Pipeline(StandardScaler + SimpleImputer(median)) + Shallow Gradient Boosting Classifier.
- **Output**: Classifier Confidence Score ($0.0 \le S \le 1.0$), Brier Score: 0.1983, ECE: 0.1142, ROC-AUC: 0.7766.
- **Guardrail**: Time-to-event variable `time` is strictly dropped to prevent look-ahead target leakage.

### 2.3. Arrhythmia 12-Lead ECG Categorizer (`arrhythmia_ecg`)
- **Dataset**: UCI Arrhythmia Database (`arrhythmia_conditions.csv`, N=430).
- **Target**: Multiclass electrophysiological categorization (5 classes: Normal, Ischemia, Old MI, Conduction Blocks, Arrhythmias).
- **Model**: Pipeline(VarianceThreshold + RobustScaler) + Balanced Random Forest (Depth 6).
- **Output**: Multiclass class probability vector.
- **Constraint**: Requires 279 quantitative 12-lead ECG measurements. Inapplicable from outpatient symptoms alone.

---

## 3. Training & Evaluation Reproduction

To retrain and evaluate the pipelines from the command line:

```powershell
# Activate project virtual environment
.\.venv\Scripts\Activate.ps1

# Run the training script for all three models
python -m Machine_Learning.src.train

# Execute pipeline unit tests and verify serialization
pytest tests/test_ml_pipeline.py -v
```

All trained artifacts are output directly to `Machine_Learning/artifacts/` with associated JSON metadata saved to `Machine_Learning/model_metadata/`.

---

## 4. Key Architectural & Safety Rules

1. **Zero Silent Imputation**: Missing predictors are never silently filled with 0.0 or mean values during inference. Missing values raise an explicit `ValueError` (or HTTP 422 at the API layer) detailing the missing keys.
2. **Deterministic Preprocessing**: Imputers, scalers, and encoders are fit strictly on training partitions to prevent data leakage.
3. **Platt Probability Calibration**: Model scores must not be represented as true clinical probabilities unless explicitly calibrated using Platt scaling or isotonic regression with measured Brier and ECE scores.
4. **Task Rejection**: Requesting predictions for tasks that lack a validated machine learning pipeline (such as general heart failure screening from outpatient symptoms) triggers an explicit rejection error.
