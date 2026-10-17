# REST API Specification & Machine-Learning Integration

**Version**: `1.0.0`  
**Base URL**: `/api/v1`  
**Protocol**: HTTPS (HTTP/1.1 for local development)  
**Encoding**: UTF-8 / JSON  
**Review Date**: 2026-10-17  

---

## 1. System Overview & Architectural Mandates

The **Heart Disease Screening and Condition-Risk Prediction System API** connects the clinical frontend with the PostgreSQL/SQLite persistence layer, rule-based clinical safety engines, and machine-learning pipelines.

### Core Architectural Principles:
1. **HIPAA & Privacy De-identification**:
   - Primary clinical keys utilize randomized, unique patient codes (e.g. `PT-4A1C8F2E`).
   - External Medical Record Numbers (MRN) are converted into one-way cryptographic SHA-256 hashes upon ingestion. Plaintext MRNs are never stored on disk.
2. **Explicit Feature Mapping (Zero Silent Imputation)**:
   - Clinical intake parameters are mapped explicitly to model inputs.
   - Raw request bodies are never passed blindly to machine-learning pipelines.
   - Missing required clinical features trigger an explicit HTTP `422 Unprocessable Entity` response with the exact missing fields listed. The API strictly prohibits silent zero or mean imputation.
3. **Calibrated Probabilities vs. Raw Classifier Scores**:
   - Coronary Artery Disease (CAD) outputs calibrated probabilities ($0.0 \le P \le 1.0$) with Brier score validation.
   - Heart Failure Mortality Risk outputs classifier confidence scores and explicitly flags that probability calibration is uncalibrated.
4. **Emergency Rule Primacy**:
   - Clinical safety triage rules operate independently of ML predictions.
   - A low ML condition-risk score is forbidden from reassuring patients presenting with red-flag emergency symptoms or critical vital signs.
   - Triggered emergency rules automatically escalate the encounter's status to `flagged_emergency` with level `EMERGENCY_IMMEDIATE_911`.
5. **Secure Document Isolation**:
   - Uploaded binary documents (PDFs, ECG reports, photos) are stored privately outside public static web roots.
   - Magic byte file signature checks prevent extension spoofing.
   - Raw uploaded files are recorded as `stored_unparsed` and are **never** claimed to be automatically interpreted unless a verified, clinician-validated extraction workflow exists.

---

## 2. Authentication & Authorization

All protected endpoints require a signed JSON Web Token (JWT) transmitted via standard HTTP Authorization header:

```http
Authorization: Bearer <access_token>
```

### Role-Based Access Control (RBAC) Matrix

| Endpoint Group | `clinician` | `admin` | `patient` | Anonymous |
| :--- | :---: | :---: | :---: | :---: |
| `/api/v1/auth/login` | Yes | Yes | Yes | Yes |
| `/api/v1/auth/me` | Yes | Yes | Yes | No (401) |
| `/api/v1/patients` (List) | All | All | Self Only | No (401) |
| `/api/v1/patients` (Create) | Yes | Yes | Forbidden (403) | No (401) |
| `/api/v1/patients/<id>` (Read/Update) | Yes | Yes | Self Only (403 if other) | No (401) |
| `/api/v1/assessments/<id>/*` | Yes | Yes | Self Only (403 if other) | No (401) |
| `/api/v1/predictions/tasks` | Yes | Yes | Yes | Yes |
| `/api/v1/recommendations/evaluate` | Yes | Yes | Yes | Yes |

### Sandbox & Demo Accounts

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `clinician_demo` | `ClinicianPass123!` | `clinician` | Attending Cardiologist (Full Access) |
| `admin_demo` | `AdminPass123!` | `admin` | System Administrator (Full Access) |
| `patient_demo` | `PatientPass123!` | `patient` | Demo Patient (Tied to Patient ID `1`) |

---

## 3. Standard Response & Error Format

### Success Envelope
```json
{
  "status": "success",
  "message": "Optional human-readable confirmation message.",
  "data": { ... },
  "meta": { ... }
}
```

### Error Envelope
```json
{
  "status": "error",
  "error": {
    "code": 422,
    "name": "Unprocessable Entity",
    "message": "Input validation failed. Please check field requirements and clinical constraints.",
    "details": [
      {
        "field": "diastolic_bp",
        "message": "Diastolic BP (130.0) cannot be greater than or equal to Systolic BP (120.0).",
        "type": "value_error"
      }
    ]
  }
}
```

---

## 4. Endpoint Reference & Synthetic Request/Response Examples

### 4.1 Authentication

#### `POST /api/v1/auth/login`
Issue a signed JWT token for valid credentials.

- **Request Body**:
```json
{
  "username": "clinician_demo",
  "password": "ClinicianPass123!"
}
```

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Authentication successful.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in_hours": 24,
    "user": {
      "id": 101,
      "username": "clinician_demo",
      "role": "clinician",
      "name": "Dr. Sarah Chen, MD",
      "email": "sarah.chen@hospital.demo",
      "patient_id": null
    }
  }
}
```

---

### 4.2 Patient Profiles & Encounters

#### `POST /api/v1/patients`
Create a new de-identified patient record. Restricted to `clinician` and `admin`.

- **Request Body**:
```json
{
  "age": 58,
  "sex": "Male",
  "medical_record_number": "MRN-SYNTH-88210",
  "notes": "Patient presented with exertional chest heaviness."
}
```

- **Response (`201 Created`)**:
```json
{
  "status": "success",
  "message": "Patient profile created successfully.",
  "data": {
    "id": 6,
    "patient_code": "PT-3F8E92B1",
    "age": 58,
    "sex": "Male",
    "is_active": true,
    "assessments_count": 0,
    "created_at": "2026-10-17T18:45:00.000000+00:00",
    "updated_at": "2026-10-17T18:45:00.000000+00:00"
  }
}
```

#### `GET /api/v1/patients`
Paginated search and filter for patient profiles.
- **Query Parameters**:
  - `page` (default `1`)
  - `per_page` (default `20`, max `100`)
  - `search` (substring match on patient code or notes)
  - `sex` (`Male` or `Female`)

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "patient_code": "DEMO-PT-CAD-001",
        "age": 63,
        "sex": "Male",
        "is_active": true,
        "assessments_count": 1,
        "created_at": "2026-10-17T12:00:00.000000+00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 20,
    "total_pages": 1
  }
}
```

#### `POST /api/v1/patients/<patient_id>/assessments`
Initiate a new clinical encounter.

- **Request Body**:
```json
{
  "reason_for_visit": "Cardiovascular risk screening and symptom evaluation.",
  "clinical_notes": "Outpatient intake assessment."
}
```

- **Response (`201 Created`)**:
```json
{
  "status": "success",
  "message": "Assessment encounter initiated successfully.",
  "data": {
    "id": 12,
    "patient_id": 6,
    "patient_code": "PT-3F8E92B1",
    "status": "in_progress",
    "reason_for_visit": "Cardiovascular risk screening and symptom evaluation.",
    "emergency_escalation_level": null,
    "assessment_date": "2026-10-17T18:46:10.000000+00:00",
    "created_at": "2026-10-17T18:46:10.000000+00:00"
  }
}
```

---

### 4.3 Symptoms and Vital Signs

#### `POST /api/v1/assessments/<assessment_id>/symptoms`
Record patient-reported symptoms. Evaluates the Diamond-Forrester angina classification and congestive score automatically.

- **Request Body**:
```json
{
  "chest_pain": true,
  "chest_pain_quality": "pressure",
  "substernal_location": true,
  "exertional_provocation": true,
  "relieved_by_rest": true,
  "dyspnea": true,
  "dyspnea_at_rest": false,
  "palpitations": false
}
```

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Symptoms recorded and classified successfully.",
  "data": {
    "id": 12,
    "assessment_id": 12,
    "chest_pain": true,
    "chest_pain_quality": "pressure",
    "substernal_location": true,
    "exertional_provocation": true,
    "relieved_by_rest": true,
    "dyspnea": true,
    "dyspnea_at_rest": false,
    "angina_classification": "typical_angina",
    "congestive_score": 1,
    "reported_at": "2026-10-17T18:47:00.000000+00:00"
  }
}
```

#### `POST /api/v1/assessments/<assessment_id>/vitals`
Record objective physiological measurements.
- Strictly validates physiological plausibility.
- Strictly stores omitted values as `null`, never as `0.0`.
- Automatically computes BMI if height and weight are provided.

- **Request Body**:
```json
{
  "systolic_bp": 142.0,
  "diastolic_bp": 88.0,
  "heart_rate": 76.0,
  "respiratory_rate": 16.0,
  "spo2": 98.0,
  "height_cm": 178.0,
  "weight_kg": 84.0
}
```

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Vitals saved successfully.",
  "data": {
    "id": 12,
    "assessment_id": 12,
    "systolic_bp": 142.0,
    "diastolic_bp": 88.0,
    "heart_rate": 76.0,
    "respiratory_rate": 16.0,
    "spo2": 98.0,
    "temperature_celsius": null,
    "height_cm": 178.0,
    "weight_kg": 84.0,
    "bmi": 26.51,
    "measured_at": "2026-10-17T18:47:30.000000+00:00"
  }
}
```

---

### 4.4 Clinical Documents and Structured Labs

#### `POST /api/v1/assessments/<assessment_id>/documents`
Upload binary medical document (PDF, PNG, JPG). Stored privately outside web directory. Magic byte signatures verified.

- **Form Data**:
  - `file`: `<resting_ecg.pdf>` (Max 10 MB)
  - `document_category`: `ecg_report_pdf`

- **Response (`201 Created`)**:
```json
{
  "status": "success",
  "message": "Document uploaded and stored successfully.",
  "data": {
    "id": 8,
    "assessment_id": 12,
    "original_filename": "resting_ecg.pdf",
    "stored_filename": "d3b07384d113edec49eaa6238ad5ff00_resting_ecg.pdf",
    "file_type": "pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 142850,
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "document_category": "ecg_report_pdf",
    "parsing_status": "stored_unparsed",
    "is_verified_by_clinician": false,
    "extraction_notice": "Document securely stored outside public directory. No automated diagnostic interpretation performed on unverified raw files."
  }
}
```

#### `POST /api/v1/assessments/<assessment_id>/labs`
Record structured lab measurements.

- **Request Body**:
```json
{
  "test_name": "cholesterol",
  "value_numeric": 238.0,
  "unit": "mg/dL",
  "reference_high": 200.0,
  "flag": "high"
}
```

- **Response (`201 Created`)**:
```json
{
  "status": "success",
  "message": "Structured laboratory measurement recorded successfully.",
  "data": {
    "id": 15,
    "assessment_id": 12,
    "test_name": "cholesterol",
    "value_numeric": 238.0,
    "value_text": null,
    "unit": "mg/dL",
    "reference_low": null,
    "reference_high": 200.0,
    "flag": "high",
    "recorded_at": "2026-10-17T18:48:00.000000+00:00"
  }
}
```

---

### 4.5 Clinical Safety & Recommendations

#### `POST /api/v1/recommendations/evaluate`
Ad-hoc clinical safety triage and secondary test recommendations.

- **Request Body**:
```json
{
  "patient_symptoms": {
    "chest_pain": true,
    "chest_pain_quality": "crushing",
    "chest_pain_radiation": "left arm",
    "substernal_location": true,
    "diaphoresis": true
  },
  "measured_vitals": {
    "systolic_bp": 94.0,
    "heart_rate": 112.0,
    "spo2": 95.0
  },
  "clinical_history": {
    "age": 61,
    "sex": "Male"
  }
}
```

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "data": {
    "status": "success",
    "is_emergency": true,
    "overall_urgency": "EMERGENCY_IMMEDIATE_911",
    "emergency_triage": {
      "is_emergency": true,
      "triggered_rules": [
        {
          "rule_id": "EMERG_001_ACUTE_CHEST_PAIN",
          "title": "Suspected Acute Coronary Syndrome (Crushing Chest Pain with Radiation)",
          "priority": "EMERGENCY_IMMEDIATE_911",
          "rationale": "Patient reported acute crushing chest pain radiating to left arm accompanied by autonomic symptoms (diaphoresis).",
          "action_guidance": "Immediately call 911/EMS. Transfer patient to nearest emergency department with cardiac catheterization capabilities.",
          "guideline_source": "2021 AHA/ACC/ASE/CHEST/SAEM/SCCT/SCMR Guideline for the Evaluation and Diagnosis of Chest Pain",
          "review_date": "2026-10-01"
        }
      ]
    },
    "symptom_evaluation": {
      "angina_classification": "typical_angina",
      "congestive_symptom_score": 0
    },
    "diagnostic_recommendations": { ... },
    "clinical_safety_notice": "EMERGENCY PRIMACY: Red-flag emergency rules supersede all other recommendations and ML predictions. If an emergency rule triggered, emergency medical services must be contacted immediately.",
    "disclaimer": "This clinical safety and recommendation engine is a research and educational prototype. It has NOT undergone formal regulatory review (e.g., FDA 510(k), CE-mark Software as a Medical Device). It does NOT replace professional clinical judgment, emergency medical services, or formal diagnostic workup. If a patient is experiencing life-threatening symptoms, immediately contact emergency services (911/112/EMS)."
  }
}
```

---

### 4.6 Machine Learning Condition-Risk Predictions

#### `GET /api/v1/predictions/tasks`
Retrieve the task catalog documenting supported models and prohibited/unsupported tasks.

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "data": {
    "supported_tasks": [
      {
        "task_name": "coronary_artery_disease",
        "supported": true,
        "score_type": "calibrated_probability",
        "is_probability_calibrated": true,
        "required_features": [
          "age", "sex", "cp", "trestbps", "chol", "fbs",
          "restecg", "thalch", "exang", "oldpeak", "slope", "ca", "thal"
        ],
        "clinical_target": "Angiographic Coronary Artery Disease (>= 50% diameter stenosis in >= 1 major vessel)",
        "clinical_limitations": "Trained on adult symptomatic cohorts undergoing diagnostic evaluation. Not for asymptomatic general screening."
      },
      {
        "task_name": "heart_failure_mortality",
        "supported": true,
        "score_type": "classifier_confidence_score",
        "is_probability_calibrated": false,
        "required_features": [
          "age", "anaemia", "creatinine_phosphokinase", "diabetes",
          "ejection_fraction", "high_blood_pressure", "platelets",
          "serum_creatinine", "serum_sodium", "sex", "smoking"
        ],
        "clinical_target": "All-Cause In-Hospital/Follow-up Mortality in Confirmed Heart Failure Patients",
        "clinical_limitations": "Valid ONLY for patients with confirmed clinical heart failure. Prohibited for general screening."
      }
    ],
    "unsupported_tasks": {
      "heart_failure_screening": "UNSUPPORTED TASK: Heart failure screening or diagnosis in the general population. The underlying dataset contains exclusively hospitalized patients with confirmed NYHA Class III-IV heart failure. There are NO non-heart-failure controls. Predicting heart failure occurrence from this dataset is medically invalid."
    }
  }
}
```

#### `POST /api/v1/assessments/<assessment_id>/predictions`
Execute inference for a supported task and persist the result with audit metadata.

- **Request Body (CAD Prediction with synthetic direct inputs)**:
```json
{
  "task_name": "coronary_artery_disease",
  "explain": true,
  "direct_features": {
    "age": 55,
    "sex": "Male",
    "cp": "typical angina",
    "trestbps": 140,
    "chol": 240,
    "fbs": false,
    "restecg": "normal",
    "thalch": 150,
    "exang": true,
    "oldpeak": 1.5,
    "slope": "flat",
    "ca": 0,
    "thal": "normal"
  }
}
```

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Prediction generated and persisted successfully.",
  "data": {
    "id": 14,
    "assessment_id": 12,
    "task_name": "coronary_artery_disease",
    "model_name": "Heart Disease Coronary Artery Disease Classifier",
    "model_version": "1.0.0",
    "target_definition": "Coronary artery disease presence (num > 0) defined as >=50% diameter stenosis in major vessels",
    "predicted_class_id": 1,
    "predicted_class_label": "Coronary Artery Disease Present (>=50% stenosis)",
    "raw_score": 0.6821,
    "calibrated_probability": 0.6821,
    "is_probability_calibrated": true,
    "decision_threshold": 0.5,
    "score_type": "calibrated_probability",
    "explanation_snapshot": {
      "method": "perturbation_sensitivity",
      "disclaimer": "Feature attributions reflect statistical pipeline associations within training cohort distributions and do NOT establish biological causation.",
      "risk_increasing_factors": [
        {"feature": "cp", "impact": "high", "direction": "risk_increasing"},
        {"feature": "exang", "impact": "moderate", "direction": "risk_increasing"}
      ],
      "risk_decreasing_factors": [
        {"feature": "ca", "impact": "moderate", "direction": "risk_decreasing"}
      ]
    },
    "clinical_prototype_disclaimer": "RESEARCH & EDUCATIONAL PROTOTYPE ONLY: This model output is generated by an uncertified research prototype. It is NOT approved as Software as a Medical Device (SaMD) by the FDA, EMA, or any regulatory body.",
    "created_at": "2026-10-17T18:49:15.000000+00:00"
  }
}
```

#### `GET /api/v1/assessments/<assessment_id>/predictions`
Retrieve the full chronological history of predictions executed on an assessment.

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 14,
      "assessment_id": 12,
      "task_name": "coronary_artery_disease",
      "model_version": "1.0.0",
      "target_definition": "Coronary artery disease presence (num > 0) defined as >=50% diameter stenosis in major vessels",
      "predicted_class_label": "Coronary Artery Disease Present (>=50% stenosis)",
      "calibrated_probability": 0.6821,
      "is_probability_calibrated": true,
      "created_at": "2026-10-17T18:49:15.000000+00:00"
    }
  ]
}
```

---

## 5. HTTP Status Code Reference

| Status Code | Reason | Clinical / System Meaning |
| :---: | :--- | :--- |
| `200` | OK | Successful GET, PUT, or ML inference request. |
| `201` | Created | Successfully created Patient, Assessment, Document, or Lab. |
| `400` | Bad Request | Malformed JSON body or requested an explicitly unsupported clinical task. |
| `401` | Unauthorized | Missing, expired, or invalid JWT Bearer token. |
| `403` | Forbidden | Insufficient role or attempt by a patient to view another patient's medical records. |
| `404` | Not Found | Target patient, assessment, document, or route does not exist. |
| `405` | Method Not Allowed | Unsupported HTTP verb on route. |
| `413` | Payload Too Large | Uploaded file or JSON body exceeds allowable limit (16 MB body, 10 MB document). |
| `422` | Unprocessable Entity | Schema validation failure, physiologically implausible vitals, or missing required ML features. |
| `500` | Internal Server Error | Unhandled database or operational server failure (transaction safely rolled back). |
| `503` | Service Unavailable | Requested model artifact or serialized pipeline not found on disk. |
