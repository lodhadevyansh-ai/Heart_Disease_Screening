# Dataset Specifications & Feasibility Assessment

**Project**: Heart Disease Screening and Condition-Risk Prediction System  
**Document**: Architectural Dataset Description & Clinical Feasibility Analysis  
**Classification**: Research & Educational Clinical Decision-Support Prototype

---

## 1. Executive Summary

This document establishes the verified clinical characteristics, statistical distributions, provenance, and modeling constraints for the three cardiovascular datasets utilized in this system:
1. **Heart Disease (UCI)**: Multi-center cohort evaluating coronary artery disease (CAD) presence and angiographic stenosis severity.
2. **Heart Failure Clinical Records**: Single-center cohort of hospitalized patients with diagnosed heart failure (NYHA III-IV) evaluating follow-up mortality.
3. **Arrhythmia Conditions**: Electrocardiographic records evaluating cardiac rhythm and conduction disorders categorized from 12-lead ECG waveforms.

---

## 2. Dataset Feasibility Matrix

| Assessment Task | Dataset Source | Target Variable | Clinical Target Definition | Input Modality Required | Outpatient Screening Feasibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Coronary Artery Disease Screening** | UCI Heart Disease | `num` (0–4) / Binary CAD (`num > 0`) | Angiographic CAD (>50% diameter stenosis) | Clinical vitals, symptoms (chest pain type), standard metabolic labs, exercise test | **FEASIBLE**: Primary inputs match outpatient triage. Missing secondary tests (`ca`, `thal`) must be handled with robust imputation. |
| **Heart Failure Follow-up Risk** | Faisalabad Heart Failure Cohort | `DEATH_EVENT` (0 or 1) | All-cause mortality during follow-up in established HF | Serum creatinine, ejection fraction, sodium, platelets, vitals | **FEASIBLE WITH CONSTRAINTS**: Valid for risk-stratifying diagnosed heart failure patients. `time` MUST be excluded from prospective inference to prevent look-ahead leakage. NOT a diagnostic tool for heart failure onset. |
| **Cardiac Arrhythmia Categorization** | UCI Arrhythmia Database | `condition_group` (5 classes) | Electrophysiological rhythm & conduction abnormalities | 279 quantitative 12-lead ECG measurements (wave intervals, amplitudes, deflections) | **UNSUPPORTED WITHOUT 12-LEAD ECG**: Symptoms (palpitations, dizziness) cannot substitute for ECG waveform deflections. System must return `PENDING_ECG` status and route to clinical safety triage. |

---

## 3. Dataset 1: Heart Disease UCI (`heart_disease_uci.csv`)

### Provenance & Citation
- **Source**: UCI Machine Learning Repository. Donated by Robert Detrano, M.D., Ph.D. (Cleveland Clinic Foundation), Andras Janosi, M.D. (Hungarian Institute of Cardiology), William Steinbrunn, M.D. (University Hospital, Zurich), and K.A. Pfisterer, M.D. (VA Medical Center, Long Beach).
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Cohort Size**: 920 patients across 4 clinical sites:
  - Cleveland: 304 patients
  - Hungarian Institute: 293 patients
  - VA Long Beach: 200 patients
  - Zurich: 123 patients

### Target Semantics & Distribution
- **Target Name**: `num`
- **Definition**: Angiographic coronary artery narrowing in any major vessel (left anterior descending, left circumflex, or right coronary artery).
- **Values**:
  - `0`: Normal / no angiographic CAD (<50% stenosis) — 411 patients (44.7%)
  - `1`: 1 vessel narrowed (>=50% stenosis) — 265 patients (28.8%)
  - `2`: 2 vessels narrowed (>=50% stenosis) — 109 patients (11.8%)
  - `3`: 3 vessels narrowed (>=50% stenosis) — 107 patients (11.6%)
  - `4`: 4 vessels narrowed (>=50% stenosis) — 28 patients (3.0%)
- **Screening Formulation**:
  - Primary Task: Binary classification (`CAD_Status = (num > 0).astype(int)`). Positive prevalence is 55.3% (509/920).
  - Secondary Task: Ordinal severity risk tiering (None, Mild, Moderate, Severe).

### Missingness, Data Entry Artifacts & Biases
- **Specialized Diagnostic Test Missingness**:
  - `ca` (fluoroscopy vessel count): Missing in 611 records (66.4%). Fluoroscopy was routinely performed at Cleveland, but rarely at the Hungarian or Swiss centers.
  - `thal` (nuclear thallium scan): Missing in 486 records (52.8%).
  - `slope` (exercise ST slope): Missing in 309 records (33.6%).
- **Physiologically Impossible Zeroes**:
  - Serum cholesterol (`chol`): 172 records contain `chol == 0`. Cholesterol levels cannot be zero in living humans; this reflects unmeasured cholesterol at Hungarian/VA sites.
  - Resting blood pressure (`trestbps`): 1 record contains `trestbps == 0`.
- **Pipeline Requirement**: Treat zeros in `chol` and `trestbps` as `NaN`. Fit imputers exclusively on training splits to prevent data leakage (Rule 9).

---

## 4. Dataset 2: Heart Failure Clinical Records (`heart_failure.csv`)

### Provenance & Citation
- **Source**: Davide Chicco, Giuseppe Jurman. *"Machine learning can predict survival of patients with heart failure from serum creatinine and ejection fraction alone"*. BMC Medical Informatics and Decision Making 20, 16 (2020).
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Cohort Size**: 299 patients (105 female, 194 male) with established NYHA Class III-IV heart failure admitted to Faisalabad Institute of Cardiology and Allied Hospital.

### Target Semantics & Critical Clinical Distinction (Rule 8)
- **Target Name**: `DEATH_EVENT`
- **Definition**: All-cause mortality event observed during the patient follow-up period.
- **Distribution**:
  - `0` (Survived through follow-up): 203 patients (67.9%)
  - `1` (Died during follow-up): 96 patients (32.1%)
- **MANDATORY CLINICAL WARNING**:
  > **This dataset does NOT evaluate the incidence, screening, or diagnosis of heart failure.**
  > Every patient in the cohort already had clinically confirmed heart failure with reduced or preserved ejection fraction.
  > Relabeling `DEATH_EVENT` as a "heart failure diagnosis" is medically false and violates Rule 8.
  > The model output must be labeled as: **Heart Failure Follow-up Mortality Risk Stratification**.

### Look-Ahead Leakage in Feature `time`
- `time` represents the follow-up duration (in days, ranging from 4 to 285 days) until either death or censoring.
- As demonstrated in the EDA, patients who suffered a `DEATH_EVENT` had a median follow-up of 44.5 days, whereas survivors had a median follow-up of 172 days.
- In prospective clinical screening, follow-up duration is a future observation that cannot be known at intake. Including `time` as an unadjusted predictor constitutes severe look-ahead leakage.
- **Architectural Policy**: Exclude `time` from prospective screening models or define fixed time-to-event horizons (e.g. 6-month survival probability).

---

## 5. Dataset 3: Arrhythmia Conditions (`arrhythmia_conditions.csv`)

### Provenance & Citation
- **Source**: UCI Arrhythmia Database. H. Altay Guvenir, Burak Acar, Haldun Demirel, Ayhan Cekin. *"A Supervised Machine Learning Algorithm for Arrhythmia Analysis"*. Computers in Cardiology 1997.
- **License**: Public academic research use.
- **Cohort Size**: 430 instances, 280 attributes.

### Target Semantics & Extreme Class Imbalance
- **Target Name**: `condition_group`
- **Classes**:
  1. `Normal`: 245 cases (57.0%)
  2. `Ischemic_MI_Related` (Ischemia, old anterior/inferior MI): 74 cases (17.2%)
  3. `Conduction_Abnormality` (Right/Left bundle branch blocks, AV blocks): 59 cases (13.7%)
  4. `Rhythm_Abnormality` (Sinus tachycardia, bradycardia, premature beats): 43 cases (10.0%)
  5. `Structural_Atrial_Abnormality` (Atrial/Ventricular hypertrophy): 9 cases (2.1%) — **Extreme Scarcity**
- **Evaluation Requirements**: Stratified cross-validation is mandatory. Macro-averaged F1 and per-class recall must be tracked; overall accuracy alone is misleading due to severe imbalance.

### Input Modality & Screening Feasibility (Rule 7 & 20)
- **Feature Structure**:
  - Columns 0–3: Demographics and physical measurements (Age, Sex, Height, Weight). Note: Feature 2 (Height) contains extreme data entry errors (up to 780 cm).
  - Columns 4–14: Global intervals (QRS, P-R, Q-T, T, P) and frontal vector angles (QRS, T, P, QRST, J). Note: Feature 13 (J-angle) has 83.3% missingness.
  - Columns 15–278: 264 quantitative waveform measurements across 12 standard ECG leads (DI–V6).
- **Clinical Feasibility Finding**:
  > **The arrhythmia dataset cannot predict arrhythmia from symptoms (palpitations, syncope) or basic outpatient labs.**
  > It requires quantitative measurements extracted from a 12-lead electrocardiogram.
- **System Architecture Rule**:
  1. If digitized 12-lead ECG waveform inputs are provided, the system executes the calibrated multi-class arrhythmia classifier.
  2. If only outpatient symptoms are available, the system outputs `Status: UNSUPPORTED_WITHOUT_ECG` with an informative message (`"Arrhythmia classification requires digitized 12-lead ECG measurements"`), and executes deterministic clinical safety rules to provide appropriate clinical testing recommendations (e.g. 12-lead resting ECG or 24-hour Holter monitoring).
