# Clinical Safety, Emergency Triage, and Recommendation Rules

## Overview and Prototype Status

This document defines the clinical decision-support rules implemented in the `clinical_rules` package:
- `clinical_rules/emergency_rules.py`
- `clinical_rules/symptom_rules.py`
- `clinical_rules/test_recommendations.py`

> [!WARNING]
> **Clinical Prototype Notice**:
> These rules represent a **research and educational clinical decision-support prototype**.
> They have NOT undergone formal regulatory clearance (such as FDA 510(k) clearance or CE-mark Software as a Medical Device).
> They do NOT replace independent medical evaluation, physical examination, emergency medical response, or definitive physician decision-making.

---

## 1. Core Safety Principles

1. **Emergency Primacy & ML Independence**:
   Emergency rules operate completely independently of machine learning model inferences. Under no circumstance may a low model score (e.g., a low predicted probability of CAD or mortality) be used to reassure a symptomatic patient, delay emergency care, or de-escalate emergency triage.
2. **Modality Distinction**:
   Patient-reported symptoms (subjective: e.g. "I feel pressure in my chest", "I get short of breath walking") are strictly distinguished from clinical measurements (objective: measured blood pressure, pulse oximetry $SpO_2$, resting heart rate).
3. **Conservative Conflict Resolution**:
   When self-reported symptoms conflict with objective vitals (e.g. self-reported "no shortness of breath" alongside an objective pulse oximetry of $SpO_2 = 88\%$, or self-reported "no chest pain" alongside detailed "crushing substernal pressure"), the system flags the conflict and resolves conservatively to protect patient safety.
4. **No Silent Assumptions on Incomplete Data**:
   Missing symptoms are tracked as unassessed rather than silently assumed absent.
5. **Secondary Testing, Not Diagnosis**:
   Diagnostic test recommendations are clinical decision-support prompts for clinician consideration based on published guideline indications. They do not constitute autonomous diagnostic conclusions or prescription orders.

---

## 2. Emergency Rules Registry (`clinical_rules/emergency_rules.py`)

**Audit Review Date**: `2026-10-01`

| Rule ID | Clinical Condition | Input Modality | Priority | Guideline Source | Action Guidance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EMERG_001_ACUTE_CORONARY_SYNDROME` | Substernal chest pressure, tightness, or heaviness radiating to left arm, neck, jaw, shoulder, or back. | Patient-Reported | Immediate (911) | AHA/ACC 2021 Chest Pain Guideline (*Circulation* 2021;144:e368-e454) | Call 911 / EMS immediately. Do not drive to hospital. Rest seated; chew aspirin 325 mg if not contraindicated. |
| `EMERG_002_CHEST_PAIN_WITH_AUTONOMIC_SIGNS` | Acute chest discomfort with unexplained cold diaphoresis (sweating), acute nausea, vomiting, or acute dyspnea. | Patient-Reported | Immediate (911) | ESC 2020 NSTE-ACS Guideline (*Eur Heart J* 2021;42:1289-1367) | Activate emergency response immediately. 12-lead ECG acquisition within 10 minutes of first medical contact. |
| `EMERG_003_ACUTE_PULMONARY_EDEMA` | Severe dyspnea at rest, inability to speak full sentences, or pink frothy sputum. | Patient-Reported | Immediate (911) | ESC 2021 Heart Failure Guidelines (*Eur Heart J* 2021;42:3599-3726) | Call 911. Position upright; do not lie flat. Immediate airway and diuretic/oxygen support. |
| `EMERG_004_CARDIAC_SYNCOPE` | Syncope during physical exertion, preceded by palpitations, or occurring while supine. | Patient-Reported | Immediate (911) | 2017 ACC/AHA/HRS Syncope Guideline (*Circulation* 2017;136:e60-e122) | Call 911 / emergency department transport. Continuous telemetry for malignant arrhythmias. |
| `EMERG_005_HYPERTENSIVE_EMERGENCY` | SBP $\ge 180$ mm Hg or DBP $\ge 120$ mm Hg with target-organ symptoms (chest pain, dyspnea, severe headache). | Clinical Measurement | Immediate (911) | 2017 ACC/AHA High Blood Pressure Guideline (*Hypertension* 2018;71:e13-e115) | Seek emergency medical care. Urgent parenteral BP reduction to prevent stroke, dissection, or MI. |
| `EMERG_006_CARDIOGENIC_SHOCK_HYPOTENSION` | Systolic BP $< 90$ mm Hg with signs of hypoperfusion (dizziness, confusion, clammy extremities). | Clinical Measurement | Immediate (911) | AHA Statement on Cardiogenic Shock (*Circulation* 2017;136:e232-e268) | Call 911. Place patient recumbent unless pulmonary edema is present. Emergency inotropic/fluid support. |
| `EMERG_007_CRITICAL_HYPOXIA` | Measured pulse oximetry $SpO_2 < 90\%$ on room air. | Clinical Measurement | Immediate (911) | WHO / AHA ACLS Emergency Care Guidelines | Call 911. Supplemental oxygen delivery and immediate respiratory evaluation. |
| `EMERG_008_HAZARDOUS_ARRHYTHMIC_VITALS` | Resting heart rate $< 40$ bpm (severe bradycardia) or $> 150$ bpm (sustained tachyarrhythmia). | Clinical Measurement | Immediate (911) | 2018 ACC/AHA/HRS Bradycardia Guideline / 2019 AHA/ACC/HRS AFib Guideline | Seek emergency department evaluation. Urgent 12-lead ECG and continuous rhythm monitoring. |
| `EMERG_009_STROKE_FAST_SIGNS` | Sudden facial droop, unilateral arm weakness, or slurred speech / difficulty speaking. | Patient-Reported | Immediate (911) | AHA/ASA Acute Ischemic Stroke Guidelines (*Stroke* 2019;50:e344-e418) | Call 911. Note exact time last seen normal. Immediate transport to certified Stroke Center. |

---

## 3. Symptom Evaluation Rules Registry (`clinical_rules/symptom_rules.py`)

**Audit Review Date**: `2026-10-01`

| Rule ID | Clinical Syndrome | Criteria & Logic | Priority | Guideline Source |
| :--- | :--- | :--- | :--- | :--- |
| `SYMP_001_ANGINA_CLASSIFICATION` | Angina Pectoris Characterization | **Diamond-Forrester / AHA 2021 Criteria**:<br>1. Substernal chest discomfort with characteristic quality and duration<br>2. Provoked by exertion or emotional stress<br>3. Relieved by rest or nitroglycerin within minutes<br><br>- 3/3 criteria: **Typical Angina** (High CAD probability)<br>- 2/3 criteria: **Atypical Angina** (Intermediate CAD probability)<br>- 0-1 criteria: **Non-Anginal Discomfort** (Low CAD probability) | Typical: Urgent Same-Day<br>Atypical: Routine Outpatient | AHA/ACC 2021 Guideline for the Evaluation and Diagnosis of Chest Pain (*Circulation* 2021;144:e368-e454) |
| `SYMP_002_HEART_FAILURE_CONGESTIVE_SIGNS` | Congestive Heart Failure Symptom Complex | Evaluates cardinal congestive symptoms:<br>- Orthopnea (sleeping on 2+ pillows)<br>- Paroxysmal Nocturnal Dyspnea (PND)<br>- Bilateral ankle/leg edema<br>- Exertional dyspnea<br>- Rapid weight gain ($\ge 2$ kg in 3 days) | $\ge 3$ signs or PND: Urgent Same-Day<br>1-2 signs: Routine Outpatient | ESC 2021 Guidelines for the Diagnosis and Treatment of Heart Failure (*Eur Heart J* 2021;42:3599-3726) |
| `SYMP_003_ARRHYTHMIC_PALPITATIONS_PATTERN` | Symptomatic Arrhythmic Palpitations | Rapid fluttering, skipped beats, or irregular rhythm associated with presyncope, dizziness, or sudden paroxysmal onset. | Presyncope: Urgent Same-Day<br>Isolated: Routine Outpatient | 2017 ACC/AHA/HRS Guideline for the Evaluation and Management of Patients With Syncope |
| `SYMP_004_INTERMITTENT_CLAUDICATION` | Peripheral Artery Disease (PAD) | Exertional calf or thigh cramping consistently provoked by walking and relieved within 10 minutes of rest. | Routine Outpatient | 2016 AHA/ACC Guideline on the Management of Patients With Lower Extremity PAD |

---

## 4. Diagnostic Test Recommendation Registry (`clinical_rules/test_recommendations.py`)

**Audit Review Date**: `2026-10-01`

| Rule ID | Diagnostic Test | Class & Evidence | Clinical Indications | Guideline Source |
| :--- | :--- | :--- | :--- | :--- |
| `REC_001_12_LEAD_ECG` | 12-Lead Resting Electrocardiogram | Class I, Level A | Chest pain, palpitations, syncope, unexplained dyspnea, or initial CAD screening. First-line electrical assessment. | AHA/ACC 2021 Chest Pain Guideline (*Circulation* 2021;144:e368-e454) |
| `REC_002_CARDIAC_TROPONIN` | High-Sensitivity Cardiac Troponin (hs-cTnI / hs-cTnT) | Class I, Level A | Acute or recent chest pain, suspected ACS, or acute ischemic dyspnea. Serial testing (0/1h or 0/2h). | ESC 2020 Guidelines for the Management of ACS (*Eur Heart J* 2021;42:1289-1367) |
| `REC_003_NATRIURETIC_PEPTIDES` | B-Type Natriuretic Peptides (BNP or NT-proBNP) | Class I, Level A | Exertional dyspnea, orthopnea, PND, or bilateral leg edema. High negative predictive value to rule out heart failure. | ESC 2021 Heart Failure Guidelines (*Eur Heart J* 2021;42:3599-3726) |
| `REC_004_TRANSTHORACIC_ECHOCARDIOGRAM` | Transthoracic Echocardiogram (TTE) | Class I, Level B | Suspected heart failure, congestive signs, new pathological murmur, syncope, or prior MI. Evaluates LVEF and valves. | 2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure (*Circulation* 2022;145:e895-e1032) |
| `REC_005_CCTA_OR_STRESS_TEST` | Coronary CTA or Functional Stress Testing | Class I, Level A | Stable chest discomfort with intermediate pretest probability of CAD (atypical or typical angina without acute ACS). | AHA/ACC 2021 Chest Pain Guideline (*Circulation* 2021;144:e368-e454) |
| `REC_006_AMBULATORY_ECG_MONITOR` | Ambulatory ECG Monitoring (Holter or Patch) | Class I, Level B | Recurrent unexplained palpitations, transient lightheadedness, or episodic presyncope. Symptom-rhythm correlation. | 2017 ACC/AHA/HRS Syncope / Arrhythmia Guidelines |
| `REC_007_CARDIOVASCULAR_METABOLIC_LABS` | Fasting Lipid, CMP, HbA1c, and CBC Panel | Class I, Level A | Cardiovascular risk screening, hypertension, diabetes, or new clinical intake. Establishes baseline ASCVD risk. | 2019 ACC/AHA Guideline on Primary Prevention of Cardiovascular Disease (*Circulation* 2019;140:e596-e646) |

---

## 5. Limitations & Boundary Safeguards

1. **No Autonomous Clinical Prescription**:
   The engine does not generate legally binding electronic laboratory orders or pharmacy prescriptions.
2. **Pediatric Exclusion**:
   All thresholds apply exclusively to adult patients ($\ge 18$ years of age). Congenital heart defects and pediatric arrhythmias are out of scope.
3. **No Substitute for 911/EMS**:
   The application UI must prominently display direct 911 / emergency contact action buttons whenever any emergency rule triggers.
