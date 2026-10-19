# Heart Disease Screening and Condition-Risk Prediction System

> [!WARNING]
> **RESEARCH & EDUCATIONAL DISCLAIMER**: This software is a clinical decision-support and educational prototype intended for research, risk stratification analysis, and symptom triage guidance. It is **NOT** an automated diagnostic system, medical device, or cleared Software as a Medical Device (SaMD). It has not undergone prospective clinical trials. Clinical decisions must always be made by licensed healthcare professionals. Emergency clinical guidance operates independently of predictive model confidence scores.

---

## 1. Project Overview

The **Heart Disease Screening and Condition-Risk Prediction System** is a full-stack clinical decision-support application. It combines calibrated machine learning models, deterministic clinical safety triage rules, relational persistence, and an interactive clinician dashboard to assist in stratified cardiovascular risk assessment.

### Key Architectural Highlights
- **Clinical Safety Primacy**: Red-flag emergency symptoms (e.g. crushing substernal chest pain, syncope, acute diaphoresis) trigger immediate emergency escalation (911) independently of machine learning scores. A low model score is strictly prevented from overriding concerning symptoms.
- **Calibrated Probabilities**: Incorporates Platt-calibrated probability models with measured Brier and Expected Calibration Error (ECE) metrics, distinguishing calibrated probabilities from raw classifier confidence scores.
- **Zero Silent Imputation**: Predictive pipelines enforce explicit feature contracts. Incomplete inputs return HTTP 422 with the exact missing fields rather than silently substituting default or mean values.
- **Privacy & Patient De-identification**: External Medical Record Numbers (MRNs) are cryptographically hashed using SHA-256 upon ingestion. Internal records are tracked via pseudorandom patient codes.
- **Secure Unparsed Document Storage**: Diagnostic reports (PDFs, ECG scans) are inspected for magic bytes, assigned sanitized UUID filenames, stored outside public static roots, and classified as `stored_unparsed` until validated by a clinician.

---

## 2. System Architecture & Tech Stack

```
Heart_Disease_Screening/
├── backend/                            # Flask REST API (Python 3.10+)
│   ├── app.py                          # Application factory & logging filter
│   ├── config.py                       # Environment configuration
│   ├── extensions.py                   # SQLAlchemy, Migrate, CORS
│   ├── routes/                         # Blueprints (auth, patient, assessment, etc.)
│   ├── schemas/                        # Marshmallow validation schemas
│   ├── services/                       # Business logic, inference runner, rules coordinator
│   └── tests/                          # Backend foundation and endpoint tests
├── clinical_rules/                     # Deterministic clinical safety engines
│   ├── emergency_rules.py              # Red-flag symptom & vital sign emergency triage
│   ├── symptom_rules.py                # Diamond-Forrester chest pain classification
│   ├── test_recommendations.py         # Secondary diagnostic test recommendations
│   └── coordinator.py                  # Unified safety coordinator with emergency primacy
├── database/                           # Relational persistence layer
│   ├── models.py                       # SQLAlchemy models (Patient, Assessment, Vitals, etc.)
│   ├── db.py                           # Session and engine management
│   ├── migrations/                     # Database schema migrations
│   └── seed_demo_data.py               # Demo database seeder script
├── frontend/                           # React 19 + Vite 8 Single-Page Application
│   ├── src/components/                 # Modular design system (forms, reports, predictions)
│   ├── src/pages/                      # 11 clinical workflow pages
│   ├── src/services/                   # Axios API clients
│   └── dist/                           # Production build bundle
├── Machine_Learning/                   # ML research, pipelines, and artifacts
│   ├── datasets/raw/                   # Archived datasets (UCI, Heart Failure, Arrhythmia)
│   ├── artifacts/                      # Serialized joblib pipelines
│   ├── model_metadata/                 # Schemas & empirical evaluation records
│   ├── notebooks/                      # Exploratory data analysis & model development
│   └── src/                            # Reusable ML training, inference, and calibration
├── docs/                               # System documentation & specifications
└── tests/                              # Pytest test suites (unit, integration, security)
```

---

## 3. Prerequisites

- **Python**: 3.10+ (Tested on Python 3.14.6)
- **Node.js**: v18+ (Tested on Node.js v26.4.0 with npm 11.17.0)
- **Operating System**: Windows, Linux, or macOS

---

## 4. Installation & Environment Setup

### 4.1. Clone the Repository
```bash
git clone https://github.com/lodhadevyansh-ai/Heart_Disease_Screening.git
cd Heart_Disease_Screening
```

### 4.2. Python Backend & ML Environment Setup
1. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install backend and machine learning dependencies:
   ```powershell
   pip install -r backend/requirements.txt
   pip install scikit-learn pandas numpy scipy imbalanced-learn xgboost shap pytest joblib
   ```

3. Configure Backend Environment:
   Copy the example environment configuration to `.env`:
   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```
   *Note*: In production, generate a secure random secret key for `SECRET_KEY` and `JWT_SECRET_KEY`.

### 4.3. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```powershell
   cd frontend
   npm install
   ```

2. Configure Frontend Environment:
   ```powershell
   Copy-Item .env.example .env
   ```
   Ensure `VITE_API_BASE_URL` points to your backend instance (default: `http://127.0.0.1:5000/api/v1`).
   Return to root directory:
   ```powershell
   cd ..
   ```

---

## 5. Database Initialization & Seeding

The application uses SQLite by default for development (stored in `instance/heart_screening.db` or configured URI) and is PostgreSQL-ready via SQLAlchemy ORM.

### 5.1. Database Reset & Clean Start
To clear demo data and start with an empty database:
```powershell
# Simulates deletion without modifying the database
python -m database.reset_data --dry-run

# Automatically backs up instance/heart_screening.db and clears clinical records
python -m database.reset_data

# Only purge synthetic demo accounts (DEMO-PT-*)
python -m database.reset_data --demo-only
```
*Note: User accounts (clinicians, administrators, patients) are strictly preserved by default during resets.*

### 5.2. Optional Demo Seeding (Test & Demonstration Only)
To seed 5 synthetic demonstration patient scenarios for evaluation:
```powershell
python -m database.seed_demo_data
```

---

## 6. Machine Learning Model Training & Artifact Locations

### 6.1. Model Artifact Locations
Serialized model pipelines and associated metadata are stored under `Machine_Learning/`:
- **CAD Model**: `Machine_Learning/artifacts/cad_model.joblib`
- **Heart Failure Mortality Model**: `Machine_Learning/artifacts/heart_failure_mortality_model.joblib`
- **Arrhythmia 12-Lead Model**: `Machine_Learning/artifacts/arrhythmia_model.joblib`
- **Evaluation Records**: `Machine_Learning/model_metadata/evaluation_metrics.json`
- **Input Feature Boundaries**: `Machine_Learning/model_metadata/feature_schema.json`

### 6.2. Retraining Pipelines
To retrain and calibrate all models from raw datasets:
```powershell
python -m Machine_Learning.src.train
```

---

## 7. Starting the Application

### 7.1. Start the Flask Backend API
From the repository root with virtual environment activated:
```powershell
python -m backend.app
```
The API server will start on `http://127.0.0.1:5000` with the versioned prefix `/api/v1`.

### 7.2. Start the React Frontend
In a separate terminal:
```powershell
cd frontend
npm run dev
```
The Vite development server will start on `http://127.0.0.1:5173`.

### 7.3. Demo Logins

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Clinician** | `clinician_demo` | `ClinicianPass123!` | Full triage dashboard, patient records, uploads, and ML predictions |
| **Patient** | `patient_demo` | `PatientPass123!` | Restricted to viewing self profile and personal assessment history |

---

## 8. Testing & Quality Assurance

### 8.1. Run Python Automated Test Suite
The project includes 139 automated tests covering ML pipelines, API response contracts, clinical rules, database integrity, integration workflows, user account management, and security controls:
```powershell
# Run the complete test suite
pytest -v

# Run specific test modules
pytest tests/test_auth_account_management.py -v
pytest tests/test_ml_pipeline.py -v
pytest tests/test_api.py -v
pytest tests/test_integration.py -v
pytest tests/test_security.py -v
```

### 8.2. Frontend Build & Lint Verification
```powershell
cd frontend

# Verify ESLint rules
npm run lint

# Execute production build bundle
npm run build
```

---

## 9. Measured Experimental Model Performance

All performance metrics below reflect **empirically measured** evaluations on held-out test splits without look-ahead target leakage:

| Task | Target Definition | Algorithm | Test $N$ | ROC-AUC | Sensitivity | Specificity | Brier Score | Calibration |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Coronary Artery Disease** | Angiographic CAD ($\ge 50\%$ stenosis) | SVC (RBF Kernel) | 184 | **0.8985** | 86.27% | 75.61% | 0.1273 | Calibrated Probability (Platt scaling, ECE: 0.0541) |
| **Heart Failure Mortality** | Follow-up mortality in confirmed HF | Gradient Boosting | 60 | **0.7766** | 31.58% | 87.80% | 0.1983 | Uncalibrated Confidence Score (ECE: 0.1142) |
| **Arrhythmia 12-Lead** | 5-class electrophysiology groups | Random Forest | 87 | **0.9016** (OvR) | 48.84% (Bal. Acc) | - | - | Uncalibrated Class Probabilities |

*For complete evaluation details, see [`docs/model_evaluation.md`](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/model_evaluation.md).*

---

## 10. Known Limitations & Research Boundaries

1. **Cleveland & Multi-Center Cohort Demographics**: The UCI Heart Disease cohort consists predominantly of male patients evaluated in hospital cardiology units in the late 1980s. Spectrum bias may lead to inflated sensitivity relative to unselected modern primary care populations.
2. **Heart Failure Cohort Scope**: The Ahmad et al. dataset comprises patients with established NYHA Class III-IV heart failure. It cannot be used to screen for initial heart failure onset in outpatients.
3. **Electrocardiographic Requirements**: The Arrhythmia model requires 279 quantitative 12-lead ECG waveform measurements. It cannot operate on patient symptoms alone.
4. **Unparsed Diagnostic Reports**: The system does not perform autonomous natural language or image extraction on uploaded diagnostic reports; they remain stored as `stored_unparsed` until entered and validated as structured measurements.
5. **Regulatory Status**: This software is not certified under HIPAA, GDPR, FDA 21 CFR Part 820, or EU MDR. It must not be deployed in production clinical environments without comprehensive clinical evaluation, privacy assessments, and regulatory approvals.

---

## 11. Documentation Directory

- [System Architecture](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/system_architecture.md)
- [Machine Learning Architecture](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/ml_architecture.md)
- [Dataset Specifications & Feasibility](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/dataset_description.md)
- [Model Evaluation & Findings](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/model_evaluation.md)
- [REST API Specification](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/api_documentation.md)
- [User Guide & Clinical Workflows](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/user_guide.md)
- [Clinical Rules Guidelines](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/clinical_rules_guidelines.md)
- [Database Schema](file:///c:/Users/lodha/Downloads/Heart_Disease_Screening/docs/database_schema.md)
