# Heart Disease Screening and Condition-Risk Prediction System

> **Disclaimer**: This software is a clinical decision-support and educational prototype intended for research, screening risk stratification, and symptom triage guidance. It is **not** an automated diagnostic system or medical device. Clinical decisions must always be made by licensed healthcare professionals. Emergency guidance operates independently of predictive model confidence scores.

---

## 1. Project Overview

The **Heart Disease Screening and Condition-Risk Prediction System** is an integrated full-stack clinical decision-support application. It combines calibrated machine learning models, deterministic clinical safety triage rules, relational persistence, and an interactive clinician dashboard to assist in stratified cardiovascular risk assessment.

### Subsystems

- **Frontend**: React 19 + Vite 8 interactive clinical dashboard.
- **Backend**: Python + Flask REST API with structured schemas and security headers.
- **Clinical Rules**: Deterministic triage for red-flag symptoms, vital sign emergencies, and secondary testing recommendations.
- **Machine Learning**: Preprocessing pipelines, calibrated classifiers, SHAP-based feature attribution, and reproducible Jupyter notebooks.
- **Database**: Relational database persistence (SQLite for development, PostgreSQL-ready via SQLAlchemy ORM).

---

## 2. Directory Structure

```text
Heart_Disease_Screening/
├── .gitignore                          # Git exclusions (virtualenvs, secrets, model caches)
├── README.md                           # Project documentation & environment setup
├── backend/                            # Flask REST API
│   ├── app.py                          # Flask application factory
│   ├── config.py                       # Configuration & environment variables
│   ├── extensions.py                   # SQLAlchemy, CORS, and extension instances
│   ├── requirements.txt                # Python backend dependencies
│   ├── routes/                         # REST API blueprints (auth, patient, prediction, etc.)
│   ├── schemas/                        # Request/response validation schemas
│   ├── services/                       # Business logic, inference runner, rule execution
│   ├── utils/                          # Error handlers, security utilities
│   └── tests/                          # Backend API tests
├── clinical_rules/                     # Deterministic clinical guidance engines
│   ├── emergency_rules.py              # Red-flag & critical symptom emergency triage
│   ├── symptom_rules.py                # Symptom-to-condition association rules
│   └── test_recommendations.py         # Secondary diagnostic test recommendations
├── database/                           # Relational data layer
│   ├── db.py                           # Database connection & session management
│   ├── models.py                       # SQLAlchemy ORM entity models
│   └── migrations/                     # Schema migrations
├── docs/                               # Architectural & ML design documentation
│   ├── ml_architecture.md
│   └── system_architecture.md
├── frontend/                           # React + Vite client
│   ├── package.json                    # Node dependencies and scripts
│   ├── vite.config.js                  # Vite configuration
│   └── src/                            # Components, pages, hooks, services, styles
├── Machine_Learning/                   # Machine learning pipelines & research
│   ├── datasets/
│   │   ├── raw/                        # Raw source CSV datasets (read-only)
│   │   │   ├── arrhythmia_conditions.csv
│   │   │   ├── heart_disease_uci.csv
│   │   │   └── heart_failure.csv
│   │   └── processed/                  # Cached processed datasets
│   ├── notebooks/                      # Research & development notebooks
│   │   ├── 01_eda.ipynb                # Cross-dataset EDA
│   │   ├── 02_heart_disease.ipynb      # UCI heart disease model development
│   │   ├── 03_heart_failure.ipynb      # Heart failure survival/mortality modeling
│   │   └── 04_arrhythmia.ipynb         # Multiclass arrhythmia ECG modeling
│   ├── model_metadata/                 # Schemas & evaluation records
│   ├── artifacts/                      # Serialized pipelines (.joblib)
│   └── src/                            # Reusable ML production modules
└── tests/                              # System & end-to-end integration tests
    ├── test_integration.py
    └── test_ml_pipeline.py
```

---

## 3. Dataset Inventory & Targets

| Dataset | File Path | Records | Features | Target Column | Clinical Definition |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Heart Disease UCI** | `Machine_Learning/datasets/raw/heart_disease_uci.csv` | 920 | 15 predictors + target | `num` (0 to 4) | Coronary artery disease presence (`num > 0`) and angiographic severity |
| **Heart Failure Clinical** | `Machine_Learning/datasets/raw/heart_failure.csv` | 299 | 12 predictors + target | `DEATH_EVENT` (0 or 1) | Survival / mortality event during follow-up for heart failure patients |
| **Arrhythmia Conditions** | `Machine_Learning/datasets/raw/arrhythmia_conditions.csv` | 430 | 279 predictors + target | `condition_group` (5 classes) | Cardiac rhythm & conduction abnormalities categorized from 12-lead ECG |

---

## 4. Environment & Prerequisites

- **Python**: 3.10+ (Tested on Python 3.14.6)
- **Node.js**: v18+ (Tested on Node.js v26.4.0, npm 11.17.0)

### Python Backend & ML Setup

1. (Recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install backend dependencies:
   ```powershell
   pip install -r backend/requirements.txt
   ```

3. ML Core packages (pandas, scikit-learn, xgboost, shap, pytest):
   ```powershell
   pip install scikit-learn pandas numpy scipy imbalanced-learn xgboost shap pytest joblib
   ```

### Frontend Setup

1. Navigate to `frontend/`:
   ```powershell
   cd frontend
   npm install
   ```

2. Start development server:
   ```powershell
   npm run dev
   ```

---

## 5. Phase Implementation Status

- [x] **Phase 1: Project Inspection and Environment Verification**
- [ ] **Phase 2: ML Pipeline & Model Training**
- [ ] **Phase 3: Clinical Decision Support & Safety Rules**
- [ ] **Phase 4: Backend REST API & Database Layer**
- [ ] **Phase 5: Frontend UI / UX Implementation**
- [ ] **Phase 6: Integration, Validation, and System Tests**
