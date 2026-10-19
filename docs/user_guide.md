# User Guide & Clinical Workflow Manual

**Project**: Heart Disease Screening and Condition-Risk Prediction System  
**Document**: Clinician & Patient User Manual  
**Classification**: Research & Educational Clinical Decision-Support Prototype  
**Date**: October 2026  

---

## 1. Introduction & Clinical Intended Use

The **Heart Disease Screening and Condition-Risk Prediction System** is a web-based clinical decision-support and risk-stratification application designed to assist healthcare personnel during outpatient cardiovascular triage.

> [!IMPORTANT]
> **Intended Use Disclaimer**: This application is a prototype intended for screening stratification, clinical risk estimation, and research education. It is **not** an automated diagnostic system or medical device. Any diagnostic determination or treatment plan must be established by a licensed healthcare provider.

---

## 2. Authentication, Account Creation & Management

### 2.1. User Account Registration
1. Navigate to `/register` or click **"Don't have an account? Create one."** on the sign-in page.
2. Complete the required fields:
   - Full Name
   - Email Address (strictly normalized and validated)
   - Account Type (Patient or Clinician)
   - Password and Confirm Password (minimum 8 characters with letters and numbers)
3. Upon registration, credentials are cryptographically hashed and a secure session token is established.

### 2.2. Roles & Preconfigured Demo Accounts

1. **Clinician (`clinician`)**:
   - Access: Complete clinician dashboard, patient registration, patient profile editing, all assessment workflows, document uploads, and ML risk predictions.
   - Demo Credentials: `clinician_demo` / `ClinicianPass123!`
2. **Patient (`patient`)**:
   - Access: Self-service patient portal. Restricted to viewing only their own demographic profile and completed assessment history. Cannot view or edit records of other patients.
   - Demo Credentials: `patient_demo` / `PatientPass123!`
3. **Administrator (`admin`)**:
   - Access: System administration and audit controls.
   - Demo Credentials: `admin_demo` / `AdminPass123!`

### 2.3. Permanent Account Deletion
1. When authenticated, navigate to **Account Settings** (`/account-settings`) via the top navigation bar or sidebar.
2. In the **Danger Zone: Permanent Account Deletion** panel, click **"Delete Account Permanently"**.
3. Re-enter your current password in the confirmation modal to authenticate the deletion request.
4. Upon confirmation:
   - Your account is permanently removed from the active database table.
   - All active tokens and sessions are immediately invalidated.
   - You will be redirected to the sign-in screen with the confirmation: *"Your account has been deleted."*
   - Any future sign-in attempts using those credentials will be rejected.

---

## 3. End-to-End Clinician Workflow

### Step 1: Accessing the Dashboard & Selecting a Patient
1. Log in with clinician credentials.
2. The **Clinician Dashboard** provides quick metrics (Total Patients, Active Assessments, Red-Flag Emergency Alerts, and Completed Screenings).
3. Select an existing patient from the **Recent Patients** table or click **"New Patient"** to register a new individual.
4. When registering a patient, enter Demographics (Age, Biological Sex) and optionally an external Medical Record Number (MRN). The system hashes the MRN using SHA-256 for privacy and generates a pseudorandom patient code (e.g., `PT-A4F109`).

### Step 2: Initiating a Clinical Assessment & Entering Symptoms
1. From the patient profile, click **"New Clinical Assessment"**.
2. Navigate to the **Symptom Assessment** tab.
3. Record presenting symptoms:
   - Chest pain presence, location, duration, and precipitating factors (exercise, stress, rest).
   - Associated symptoms: Dyspnea (shortness of breath), diaphoresis (cold sweat), palpitations, syncope (fainting), radiation to jaw/left arm.
4. Click **"Save Symptoms & Evaluate Triage"**.

### Step 3: Immediate Emergency Rule Evaluation (Safety Primacy)
1. The clinical rules engine evaluates red-flag symptoms immediately upon submission.
2. If acute life-threatening criteria are detected (e.g., crushing substernal chest pain with diaphoresis or syncope):
   - A high-visibility **Emergency Alert Banner (CRITICAL 911)** will appear immediately at the top of the interface.
   - Guidance instructions prompt immediate transfer to the Emergency Department / EMS activation.
   - **Crucial Rule**: The emergency alert operates completely independently of machine learning scores. It cannot be cleared or dismissed by a low ML risk prediction.

### Step 4: Clinical Recommendations & Diagnostic Guidance
1. Click the **Test Recommendations** tab.
2. Review evidence-based secondary testing guidance generated from the patient's symptoms:
   - For suspected acute coronary syndromes: 12-lead ECG and serial high-sensitivity Troponin.
   - For suspected heart failure/dyspnea: NT-proBNP and Transthoracic Echocardiogram (TTE).
   - For palpitations/syncope: 24-hour ambulatory Holter monitor.
   - For stable intermediate-risk chest pain: Coronary CT Angiography (CCTA) or exercise treadmill stress test.

### Step 5: Recording Vital Signs & Structured Laboratory Measurements
1. Navigate to the **Vitals & Labs** / **Report Management** tab.
2. Enter physical examination vitals:
   - Resting Blood Pressure (Systolic / Diastolic in mmHg).
   - Heart Rate (bpm).
   - Body Mass Index (BMI in $\text{kg/m}^2$, automatically calculated from height and weight).
3. Enter structured laboratory values:
   - Total Serum Cholesterol (mg/dL).
   - Fasting Blood Sugar (mg/dL).
   - Serum Creatinine (mg/dL) and Serum Sodium (mEq/L).
   - Resting Electrocardiogram (Normal, ST-T wave abnormality, Left Ventricular Hypertrophy).
4. Save vitals and structured values. Note: Unmeasured fields remain stored as NULL and are clearly distinguished from genuine zero values.

### Step 6: Diagnostic Document & Report Management
1. If diagnostic report files (PDF summaries, ECG scans, laboratory printouts) are available, upload them in the **Report Management** section.
2. Accepted formats: `.pdf`, `.png`, `.jpg`, `.jpeg` (Max size: 16 MB).
3. Uploaded documents are stored privately with sanitized UUID filenames outside public web roots.
4. **Notice on Document Extraction**: Uploaded documents are assigned the status `stored_unparsed`. The system does **not** claim to automatically interpret raw document text unless a clinician has validated structured manual inputs.

### Step 7: Predictive Condition-Risk Stratification & SHAP Interpretation
1. Navigate to the **Condition Risk Prediction** tab.
2. Select the appropriate clinical task:
   - **Coronary Artery Disease Risk**: Evaluates the probability of $\ge 50\%$ diameter coronary artery stenosis.
   - **Heart Failure Mortality Risk**: Stratifies follow-up mortality risk for patients with confirmed heart failure.
3. Click **"Run Risk Prediction"**.
4. Review the structured output:
   - **Risk Tier Badge**: Low Risk, Moderate Risk, High Risk, or Critical.
   - **Calibrated Probability**: A Platt-calibrated probability score with Brier metric context (for CAD).
   - **Feature Attribution Chart**: SHAP bar chart highlighting the clinical factors contributing most significantly to the score.
   - **Standard Clinical Disclaimer**: Reinforcing that statistical correlations require physician verification.

### Step 8: Longitudinal Assessment History
1. Navigate to **Assessment History** to review previous screening encounters for the patient.
2. Compare risk trajectory and observe changes in symptom severity over time.

---

## 4. Patient Self-Service Portal

1. Patients log in with their assigned username and credentials.
2. The patient portal provides:
   - Demographics and assigned patient code.
   - Past completed assessments with plain-language clinical guidance summaries.
   - Clear instructions to seek emergency services (911) if they experience chest pain, severe shortness of breath, or fainting.
   - Strict privacy safeguards: Cross-patient access attempts are rejected with HTTP 403 Forbidden.

---

## 5. Frequently Asked Questions (FAQ)

**Q: Why was my heart failure screening prediction rejected?**  
*A: Outpatient general heart failure screening is not supported by the Ahmad et al. dataset, which is restricted to follow-up survival for hospitalized patients with diagnosed heart failure. The system refuses clinically invalid task queries by design.*

**Q: Can I run the Arrhythmia model with patient symptoms alone?**  
*A: No. The arrhythmia model requires quantitative 12-lead ECG waveform measurements (intervals, amplitudes). Attempting to run it without ECG parameters will return an explicit missing feature error.*

**Q: What happens if a patient's cholesterol is missing?**  
*A: The system enforces explicit feature contracts. If a mandatory feature for a specific model is missing, the API responds with HTTP 422 Unprocessable Entity detailing the missing parameter. It will not silently impute a zero or mean.*
