"""
Diagnostic Test Recommendation Engine.

Generates evidence-based secondary diagnostic testing recommendations aligned
with international cardiovascular clinical practice guidelines (AHA/ACC, ESC).

CRITICAL CLINICAL DIRECTIVES:
1. DECISION SUPPORT ONLY: Recommendations are educational suggestions for healthcare
   provider consideration. They do NOT constitute an automated prescription, clinical
   order, or definitive diagnostic conclusion.
2. EVIDENCE-BASED THRESHOLDS: Testing triggers are strictly anchored to published Class I
   and Class IIa guideline indications, never arbitrary convenience.
3. PREVENT OVER-TESTING: In low-risk, asymptomatic patients, routine high-cost imaging
   (e.g., CCTA, stress SPECT) is actively withheld to prevent unnecessary radiation and incidentalomas.
"""

from typing import Any, Dict, List, Optional, Union
from clinical_rules import (
    CLINICAL_SAFETY_DISCLAIMER,
    ClinicalRuleResult,
    InputModality,
    RulePriority,
)

REVIEW_DATE = "2026-10-01"


def generate_test_recommendations(
    patient_symptoms: Optional[Dict[str, Any]] = None,
    measured_vitals: Optional[Dict[str, Any]] = None,
    clinical_history: Optional[Dict[str, Any]] = None,
    symptom_eval: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate evidence-based diagnostic test recommendations based on patient presentation.
    
    Parameters
    ----------
    patient_symptoms : dict, optional
        Reported symptoms (chest pain, dyspnea, palpitations, syncope, etc.).
    measured_vitals : dict, optional
        Vitals (BP, HR, SpO2).
    clinical_history : dict, optional
        Past medical history, age, sex, diabetes, hypertension, smoking.
    symptom_eval : dict, optional
        Pre-computed output from evaluate_symptom_rules().
        
    Returns
    -------
    dict
        Structured recommendations including:
        - recommendations: list of dict
        - recommended_test_names: list of str
        - priority_breakdown: dict
        - provider_guidance: str
        - clinical_disclaimer: str
    """
    symptoms = patient_symptoms or {}
    vitals = measured_vitals or {}
    history = clinical_history or {}

    angina_class = symptom_eval.get("angina_classification", "none") if symptom_eval else "none"
    congestive_score = symptom_eval.get("congestive_symptom_score", 0) if symptom_eval else 0

    has_chest_pain = bool(symptoms.get("chest_pain", False) or symptoms.get("chest_pressure", False) or angina_class in ["typical_angina", "atypical_angina"])
    has_dyspnea = bool(symptoms.get("dyspnea", False) or symptoms.get("shortness_of_breath", False) or congestive_score > 0)
    has_palpitations = bool(symptoms.get("palpitations", False))
    has_syncope = bool(symptoms.get("syncope", False) or symptoms.get("loss_of_consciousness", False))
    has_edema = bool(symptoms.get("bilateral_leg_edema", False) or symptoms.get("ankle_edema", False))
    has_hypertension = bool(history.get("hypertension", False) or history.get("high_blood_pressure", False))
    has_diabetes = bool(history.get("diabetes", False))

    recommendations: List[ClinicalRuleResult] = []

    # -------------------------------------------------------------------------
    # TEST 1: Resting 12-Lead Electrocardiogram (ECG)
    # -------------------------------------------------------------------------
    # Indication: Chest pain, palpitations, syncope, unexplained dyspnea, or initial CAD workup
    ecg_indicated = has_chest_pain or has_palpitations or has_syncope or has_dyspnea or has_hypertension
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_001_12_LEAD_ECG",
            category="recommendation",
            title="12-Lead Resting Electrocardiogram (ECG)",
            triggered=ecg_indicated,
            priority=RulePriority.URGENT_SAME_DAY if (has_chest_pain or has_syncope) else RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "First-line resting electrophysiological assessment. Evaluates for acute ischemia "
                "(ST-segment elevation/depression, T-wave inversion), prior myocardial infarction "
                "(pathological Q waves), conduction delays (LBBB, RBBB), pre-excitation, and arrhythmias."
            ),
            action_guidance=(
                "Order a standard resting 12-lead ECG. If acute ischemic symptoms are present, "
                "ECG acquisition and physician interpretation must occur within 10 minutes of arrival."
            ),
            guideline_source="AHA/ACC 2021 Guideline for the Evaluation and Diagnosis of Chest Pain (Circulation 2021;144:e368-e454)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level A", "test_code": "ECG_12LEAD"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 2: High-Sensitivity Cardiac Troponin (hs-cTn)
    # -------------------------------------------------------------------------
    # Indication: Acute or recent chest pain, suspected ACS, or acute ischemic dyspnea
    troponin_indicated = has_chest_pain or (has_dyspnea and bool(symptoms.get("diaphoresis", False)))
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_002_CARDIAC_TROPONIN",
            category="recommendation",
            title="High-Sensitivity Cardiac Troponin (hs-cTnI or hs-cTnT)",
            triggered=troponin_indicated,
            priority=RulePriority.EMERGENCY_IMMEDIATE if has_chest_pain else RulePriority.URGENT_SAME_DAY,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "Gold-standard biomarker of acute myocardial cellular necrosis. Essential to rule in "
                "or rule out Non-ST-Segment Elevation Myocardial Infarction (NSTEMI) using rapid validated "
                "0/1-hour or 0/2-hour serial sampling protocols."
            ),
            action_guidance=(
                "Order emergency serial hs-cTn testing at presentation and 1 to 2 hours later. "
                "Interpret levels relative to sex-specific 99th percentile upper reference limits."
            ),
            guideline_source="ESC 2020 Guidelines for the Management of Acute Coronary Syndromes (Eur Heart J 2021;42:1289-1367)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level A", "test_code": "LAB_HS_TROPONIN"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 3: B-Type Natriuretic Peptides (BNP or NT-proBNP)
    # -------------------------------------------------------------------------
    # Indication: Exertional or rest dyspnea, orthopnea, PND, peripheral edema, suspected HF
    bnp_indicated = has_dyspnea or has_edema or (congestive_score >= 1)
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_003_NATRIURETIC_PEPTIDES",
            category="recommendation",
            title="Natriuretic Peptides (BNP or NT-proBNP)",
            triggered=bnp_indicated,
            priority=RulePriority.URGENT_SAME_DAY if congestive_score >= 2 else RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "Biomarker of ventricular wall stress. High negative predictive value to rule out "
                "heart failure as the primary cause of dyspnea or peripheral edema (non-acute cutoffs: "
                "BNP < 35 pg/mL, NT-proBNP < 125 pg/mL)."
            ),
            action_guidance=(
                "Order serum BNP or NT-proBNP. Elevated levels warrant follow-up echocardiography "
                "to evaluate systolic and diastolic ventricular performance."
            ),
            guideline_source="ESC 2021 Guidelines for the Diagnosis and Treatment of Acute and Chronic Heart Failure (Eur Heart J 2021;42:3599-3726)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level A", "test_code": "LAB_BNP"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 4: Transthoracic Echocardiogram (TTE)
    # -------------------------------------------------------------------------
    # Indication: Suspected heart failure, abnormal murmur, congestive signs, prior MI
    tte_indicated = (congestive_score >= 1) or has_syncope or bool(history.get("prior_mi", False)) or bool(symptoms.get("heart_murmur", False))
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_004_TRANSTHORACIC_ECHOCARDIOGRAM",
            category="recommendation",
            title="Transthoracic Echocardiogram (TTE)",
            triggered=tte_indicated,
            priority=RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "Non-invasive ultrasound assessment of cardiac structure and hemodynamics. Evaluates "
                "left ventricular ejection fraction (LVEF), regional wall motion abnormalities, "
                "valvular stenosis/regurgitation, chamber dimensions, and pericardial effusion."
            ),
            action_guidance=(
                "Schedule comprehensive 2D and Doppler transthoracic echocardiography to phenotypically "
                "characterize ventricular function (HFrEF vs HFpEF) or valvular etiology."
            ),
            guideline_source="2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure (Circulation 2022;145:e895-e1032)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level B", "test_code": "IMG_TTE"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 5: Non-Invasive CAD Evaluation (CCTA or Stress Testing)
    # -------------------------------------------------------------------------
    # Indication: Intermediate-risk stable chest discomfort (typical or atypical angina without acute ACS)
    stress_ccta_indicated = angina_class in ["typical_angina", "atypical_angina"] and not bool(symptoms.get("diaphoresis", False))
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_005_CCTA_OR_STRESS_TEST",
            category="recommendation",
            title="Coronary Computed Tomography Angiography (CCTA) or Functional Stress Test",
            triggered=stress_ccta_indicated,
            priority=RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "In stable chest discomfort with intermediate pretest probability of CAD, CCTA is "
                "recommended for anatomical exclusion of obstructive stenosis and plaque characterization, "
                "or functional stress testing (Stress Echo/SPECT/CMR) to detect inducible myocardial ischemia."
            ),
            action_guidance=(
                "Refer for outpatient CCTA (preferred in patients < 65 without extensive calcification) "
                "or functional stress imaging based on institutional expertise and patient renal/rhythm status."
            ),
            guideline_source="AHA/ACC 2021 Guideline for the Evaluation and Diagnosis of Chest Pain (Circulation 2021;144:e368-e454)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level A", "test_code": "IMG_CCTA_STRESS"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 6: Ambulatory ECG Monitoring (Holter or Patch Monitor)
    # -------------------------------------------------------------------------
    # Indication: Recurrent unexplained palpitations, episodic presyncope, or suspected intermittent arrhythmia
    holter_indicated = has_palpitations or (has_syncope and not has_chest_pain)
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_006_AMBULATORY_ECG_MONITOR",
            category="recommendation",
            title="Ambulatory ECG Monitoring (24-48h Holter or Extended Patch Monitor)",
            triggered=holter_indicated,
            priority=RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "Continuous ambulatory cardiac rhythm recording to correlate transient palpitations "
                "or lightheadedness with objective rhythm disturbances (e.g., paroxysmal atrial fibrillation, "
                "supraventricular tachycardia, premature ventricular contractions, sinus pauses)."
            ),
            action_guidance=(
                "Order 24-48 hour Holter monitor (for daily symptoms) or 7-14 day extended patch monitor "
                "(for intermittent symptoms occurring weekly) with patient symptom event logging."
            ),
            guideline_source="2017 ACC/AHA/HRS Guideline for the Evaluation and Management of Patients With Syncope / Arrhythmia",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level B", "test_code": "MON_HOLTER"},
        )
    )

    # -------------------------------------------------------------------------
    # TEST 7: Cardiovascular Metabolic & Renal Laboratory Panel
    # -------------------------------------------------------------------------
    # Indication: Cardiovascular risk factor assessment, hypertension, diabetes, or new intake
    lab_indicated = has_hypertension or has_diabetes or bool(history.get("smoking", False)) or bool(history.get("age", 0) >= 40)
    recommendations.append(
        ClinicalRuleResult(
            rule_id="REC_007_CARDIOVASCULAR_METABOLIC_LABS",
            category="recommendation",
            title="Comprehensive Metabolic, Lipid & Renal Laboratory Panel",
            triggered=lab_indicated,
            priority=RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.COMBINED_ASSESSMENT,
            rationale=(
                "Fasting lipid panel (total, LDL-C, HDL-C, triglycerides), fasting glucose/HbA1c, "
                "serum creatinine with estimated GFR, serum electrolytes, and CBC. Establishes baseline "
                "atherosclerotic risk profile and identifies secondary contributors to dyspnea (anemia)."
            ),
            action_guidance=(
                "Order fasting lipid panel, comprehensive metabolic panel (CMP), and CBC. "
                "Calculate 10-year ASCVD risk score once laboratory values are finalized."
            ),
            guideline_source="2019 ACC/AHA Guideline on the Primary Prevention of Cardiovascular Disease (Circulation 2019;140:e596-e646)",
            review_date=REVIEW_DATE,
            metadata={"recommendation_class": "Class I", "level_of_evidence": "Level A", "test_code": "LAB_METABOLIC_PANEL"},
        )
    )

    # Filter triggered recommendations
    triggered_recs = [r for r in recommendations if r.triggered]

    return {
        "recommendations_count": len(triggered_recs),
        "recommendations": [r.to_dict() for r in triggered_recs],
        "all_considered_tests": [r.to_dict() for r in recommendations],
        "recommended_test_names": [r.title for r in triggered_recs],
        "provider_guidance": (
            "These testing suggestions are derived from published clinical practice guidelines "
            "to assist clinical decision-making. The treating clinician must determine test "
            "appropriateness based on patient-specific contraindications, renal function, and local resources."
        ),
        "clinical_disclaimer": CLINICAL_SAFETY_DISCLAIMER,
    }
