# Dataset Documentation & Data Dictionary
## Heart Disease Screening and Condition-Risk Prediction System

This document outlines the clinical provenance, schema, target definitions, missingness patterns, and architectural limitations of the raw datasets stored in `Machine_Learning/datasets/raw/`.

---

## 1. Storage & Integrity Guidelines

- **Immutability**: Files in `Machine_Learning/datasets/raw/` are **read-only source archives**. They must never be edited, deleted, or overwritten by any analysis script or training pipeline.
- **Derived Datasets**: Any imputed, transformed, or partitioned training sets must be directed to `Machine_Learning/datasets/processed/`.
- **Target Independence**: Each dataset addresses a distinct clinical population and outcome. No arbitrary blending into a single composite probability score is permitted without validated clinical calibration.

---

## 2. Dataset 1: Heart Disease UCI (`heart_disease_uci.csv`)

### Provenance & Citation
- **Source**: UCI Machine Learning Repository / Cleveland Clinic Foundation, Hungarian Institute of Cardiology, University Hospital Zurich, VA Medical Center Long Beach.
- **Principal Investigators**: Robert Detrano, M.D., Ph.D.; Andras Janosi, M.D.; William Steinbrunn, M.D.; K.A. Pfisterer, M.D.
- **License / Terms**: Open access for research and education with proper attribution (Creative Commons Attribution 4.0 International).

### Characteristics
- **Dimensions**: 920 rows × 16 columns
- **Duplicate Rows**: 0
- **Missing Values**:
  - `ca` (major vessels colored by fluoroscopy): 611 missing (66.4%)
  - `thal` (thallium heart scan): 486 missing (52.8%)
  - `slope` (peak exercise ST slope): 309 missing (33.6%)
  - `fbs` (fasting blood sugar > 120 mg/dl): 90 missing (9.8%)
  - `oldpeak` (ST depression): 62 missing (6.7%)
  - `trestbps` (resting blood pressure): 59 missing (6.4%)
  - `thalch` (maximum heart rate achieved): 55 missing (6.0%)
  - `exang` (exercise-induced angina): 55 missing (6.0%)
  - `chol` (serum cholesterol): 30 missing (3.3%)
  - `restecg` (resting ECG results): 2 missing (0.2%)

### Target Variable
- **Target Column**: `num`
- **Clinical Meaning**: Angiographic coronary artery disease (CAD) status determined by coronary angiography (>50% diameter narrowing in one or more major coronary vessels).
  - `0`: No angiographic CAD (<50% diameter stenosis) — 411 patients (44.7%)
  - `1`: Mild single-vessel CAD — 265 patients (28.8%)
  - `2`: Moderate two-vessel CAD — 109 patients (11.8%)
  - `3`: Severe three-vessel CAD — 107 patients (11.6%)
  - `4`: Critical multi-vessel CAD — 28 patients (3.0%)
- **Binary Classification Formulation**: `CAD_Status = (num > 0).astype(int)` (411 negative, 509 positive).

### Feature Dictionary
| Column | Type | Description | Values / Units |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Patient identifier | 1 to 920 |
| `age` | Integer | Patient age | Years (28 to 77) |
| `sex` | String | Biological sex | `Male`, `Female` |
| `dataset` | String | Data collection site | `Cleveland`, `Hungary`, `Switzerland`, `VA Long Beach` |
| `cp` | String | Chest pain type | `typical angina`, `atypical angina`, `non-anginal`, `asymptomatic` |
| `trestbps` | Float | Resting blood pressure | mm Hg on hospital admission |
| `chol` | Float | Serum cholesterol | mg/dL |
| `fbs` | Object | Fasting blood sugar > 120 mg/dL | `True`, `False` |
| `restecg` | String | Resting electrocardiographic results | `normal`, `lv hypertrophy`, `st-t abnormality` |
| `thalch` | Float | Maximum heart rate achieved during exercise | Beats per minute (71 to 202) |
| `exang` | Object | Exercise-induced angina | `True`, `False` |
| `oldpeak` | Float | ST depression induced by exercise relative to rest | mm (-2.6 to 6.2) |
| `slope` | String | Slope of peak exercise ST segment | `upsloping`, `flat`, `downsloping` |
| `ca` | Float | Number of major vessels (0-3) colored by fluoroscopy | 0.0, 1.0, 2.0, 3.0 |
| `thal` | String | Thallium scintigraphy defect status | `normal`, `fixed defect`, `reversable defect` |

### Known Anomalies & Clinical Caveats
1. **Physiologically Impossible Zeros**: 172 records have `chol == 0` and 1 record has `trestbps == 0`. These are unmeasured lab values recorded as 0 at Hungarian and Swiss clinics. They must be treated as `NaN` and imputed.
2. **Site Selection Bias**: Specialized tests (`ca` and `thal`) were ordered routinely at Cleveland but rarely at other sites, creating non-random missingness.

---

## 3. Dataset 2: Heart Failure Clinical Records (`heart_failure.csv`)

### Provenance & Citation
- **Source**: Davide Chicco, Giuseppe Jurman: *"Machine learning can predict survival of patients with heart failure from serum creatinine and ejection fraction alone"*. BMC Medical Informatics and Decision Making 20, 16 (2020).
- **Cohort**: 299 patients with heart failure (NYHA Class III-IV) collected at the Faisalabad Institute of Cardiology and Allied Hospital (Pakistan).
- **License / Terms**: Open access under Creative Commons Attribution 4.0 International (CC BY 4.0).

### Characteristics
- **Dimensions**: 299 rows × 13 columns
- **Duplicate Rows**: 0
- **Missing Values**: 0 (Complete dataset)

### Critical Clinical Target Definition (Mandatory Rule 8)
- **Target Column**: `DEATH_EVENT` (Binary: `0` = Survived follow-up, `1` = Deceased during follow-up).
- **Distribution**: `0`: 203 patients (67.9%), `1`: 96 patients (32.1%).
- **CRITICAL ARCHITECTURAL DISTINCTION**:
  > **`DEATH_EVENT` is a post-admission mortality endpoint in patients who already have heart failure.**
  > It is **NOT** a diagnosis of whether heart failure is present.
  > The application must label outputs from this model as **Heart Failure Mortality / Survival Risk**, never as a heart failure diagnosis.

### Feature Dictionary
| Column | Type | Clinical Description | Reference Range / Units |
| :--- | :--- | :--- | :--- |
| `age` | Float | Patient age | Years (40 to 95) |
| `anaemia` | Integer | Decrease of red blood cells or hemoglobin | `0` = No, `1` = Yes |
| `creatinine_phosphokinase` | Integer | Level of CPK enzyme in blood | mcg/L (23 to 7861) |
| `diabetes` | Integer | Patient history of diabetes mellitus | `0` = No, `1` = Yes |
| `ejection_fraction` | Integer | Percentage of blood leaving the left ventricle per contraction | % (14 to 80; <40% indicates heart failure with reduced EF) |
| `high_blood_pressure` | Integer | History of hypertension | `0` = No, `1` = Yes |
| `platelets` | Float | Platelet count in blood | kiloplatelets/mL (25,100 to 850,000) |
| `serum_creatinine` | Float | Level of serum creatinine in blood | mg/dL (0.5 to 9.4) |
| `serum_sodium` | Integer | Level of serum sodium in blood | mEq/L (113 to 148) |
| `sex` | Integer | Biological sex | `0` = Female, `1` = Male |
| `smoking` | Integer | Tobacco smoking history | `0` = No, `1` = Yes |
| `time` | Integer | Follow-up observation duration | Days (4 to 285) |
| `DEATH_EVENT` | Integer | All-cause mortality event during follow-up | `0` = Survived, `1` = Deceased |

### Data Leakage & Clinical Caveat (Feature `time`)
- **Look-Ahead Target Leakage**: The feature `time` records how many days elapsed before the patient either died or completed the study. In prospective screening at initial triage, future follow-up duration is **completely unknown**.
- **Architectural Rule**: The prospective inference pipeline must **exclude `time` as a feature** or formulate predictions under calibrated time horizons without conditioning on actual survival duration.

---

## 4. Dataset 3: Arrhythmia Conditions (`arrhythmia_conditions.csv`)

### Provenance & Citation
- **Source**: UCI Arrhythmia Database / Bilkent University (H. Altay Guvenir et al., 1997).
- **Objective**: Distinguish between normal ECG patterns and different categories of cardiac arrhythmias.
- **License / Terms**: Open access for educational/academic research with proper citation.

### Characteristics
- **Dimensions**: 430 rows × 280 columns
- **Duplicate Rows**: 0
- **Missing Values**:
  - Column `13` (J-wave vector angle): 358 missing (83.3%)
  - Column `11` (P-wave vector angle): 19 missing (4.4%)
  - Column `10` (T-wave vector angle): 7 missing (1.6%)
  - Column `12` (QRST vector angle): 1 missing (0.2%)
  - Column `14` (Heart rate): 1 missing (0.2%)

### Target Variable
- **Target Column**: `condition_group` (Categorical String, 5 classes):
  1. `Normal`: 245 instances (57.0%)
  2. `Ischemic_MI_Related`: 74 instances (17.2%)
  3. `Conduction_Abnormality`: 59 instances (13.7%)
  4. `Rhythm_Abnormality`: 43 instances (10.0%)
  5. `Structural_Atrial_Abnormality`: 9 instances (2.1%) — **Extreme Class Imbalance**

### Feature Breakdown
- **Demographics & Physical Attributes** (Columns 0–3): Age, Sex, Height, Weight.
- **Global Electrocardiographic Intervals & Angles** (Columns 4–14):
  - QRS duration, P-R interval, Q-T interval, T interval, P interval.
  - Frontal plane vector angles: QRS, T, P, QRST, J.
  - Resting heart rate.
- **12-Lead Quantitative Waveform Metrics** (Columns 15–278):
  - 12 standard leads: DI, DII, DIII, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6.
  - Per lead: Width, amplitude, and deflections for Q, R, S, R', S' waves; ST segment displacement; T wave amplitude; and total integral areas.

### Input Feasibility & Screening Reality (Mandatory Rule 7 & 20)
- **Clinical Feasibility Finding**:
  > **This dataset CANNOT predict arrhythmia from patient symptoms (e.g. palpitations, lightheadedness) or routine laboratory values.**
  > It requires 279 specialized numerical measurements extracted from a digitized 12-lead electrocardiogram.
- **System Policy**:
  - In outpatient screening when only symptom reports are provided, the system **must NOT** run the arrhythmia ML model with fabricated or default values.
  - The UI and API must return an explicit status: `Status: PENDING_ECG_DIAGNOSTICS`, accompanied by deterministic clinical safety recommendations (e.g. 12-lead ECG referral or Holter monitoring) derived from symptom rules.
