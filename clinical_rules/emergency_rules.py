"""
Emergency Clinical Rules Engine.

Evaluates red-flag symptoms and critical vital sign abnormalities that mandate
immediate emergency medical escalation (EMS / 911 / Emergency Department).

CRITICAL SAFETY DIRECTIVES:
1. INDEPENDENCE FROM ML: Emergency rules operate completely independently of any
   machine learning model prediction. A low ML risk score (e.g., predicted CAD probability
   of 0.05) CANNOT and MUST NEVER be used to reassure a patient with red-flag symptoms
   or de-escalate emergency triage.
2. MODALITY SEPARATION: Distinguishes self-reported patient symptoms from measured
   vital signs.
3. PROTOCOL INTEGRITY: All rules are derived from published clinical practice guidelines
   (AHA/ACC, ESC) with recorded review dates and evidentiary citations.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from clinical_rules import (
    CLINICAL_SAFETY_DISCLAIMER,
    ClinicalRuleResult,
    InputModality,
    RulePriority,
)

REVIEW_DATE = "2026-10-01"


def evaluate_emergency_rules(
    patient_symptoms: Optional[Dict[str, Any]] = None,
    measured_vitals: Optional[Dict[str, Any]] = None,
    ml_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate red-flag cardiovascular symptoms and critical measured vital abnormalities.
    
    Parameters
    ----------
    patient_symptoms : dict, optional
        Self-reported symptoms (e.g., chest pain quality, radiation, shortness of breath, syncope).
    measured_vitals : dict, optional
        Clinically measured physiological metrics (e.g., systolic BP, diastolic BP, heart rate, SpO2).
    ml_context : dict, optional
        Outputs from machine learning pipelines. Included ONLY to test and document that
        low ML scores are forbidden from overriding emergency escalations.
        
    Returns
    -------
    dict
        Structured emergency evaluation containing:
        - is_emergency: bool
        - escalation_level: str ('EMERGENCY_IMMEDIATE_911', 'URGENT_EMERGENCY_DEPARTMENT', 'NONE')
        - triggered_rules: list of dict
        - all_evaluated_rules: list of dict
        - emergency_action_plan: list of str
        - ml_override_safeguard: str
        - disclaimer: str
    """
    symptoms = patient_symptoms or {}
    vitals = measured_vitals or {}

    evaluated_rules: List[ClinicalRuleResult] = []

    # -------------------------------------------------------------------------
    # RULE 1: Acute Ischemic Chest Pain / Suspected Acute Coronary Syndrome (ACS)
    # -------------------------------------------------------------------------
    cp_presence = bool(symptoms.get("chest_pain", False) or symptoms.get("chest_pressure", False))
    cp_quality = str(symptoms.get("chest_pain_quality", "")).lower()
    cp_radiation = str(symptoms.get("chest_pain_radiation", "")).lower()
    radiates_to_arm_jaw = any(loc in cp_radiation for loc in ["left arm", "arm", "jaw", "neck", "shoulder", "back"])
    is_crushing = any(q in cp_quality for q in ["crushing", "heavy", "pressure", "tightness", "squeezing", "constricting"])
    
    r1_triggered = cp_presence and (radiates_to_arm_jaw or is_crushing)
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_001_ACUTE_CORONARY_SYNDROME",
            category="emergency",
            title="Acute Ischemic Chest Pain / Suspected Acute Coronary Syndrome",
            triggered=r1_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Patient reports substernal chest pressure, tightness, or heaviness radiating "
                "to the left arm, jaw, neck, shoulder, or back. This symptom complex strongly "
                "suggests acute myocardial ischemia or acute coronary syndrome."
            ),
            action_guidance=(
                "CALL 911 / EMERGENCY MEDICAL SERVICES IMMEDIATELY. "
                "Do not drive yourself to the hospital. Have the patient sit down, remain calm, "
                "and chew an aspirin (325 mg) if not allergic and not contraindicated, pending EMS arrival."
            ),
            guideline_source="AHA/ACC 2021 Guideline for the Evaluation and Diagnosis of Chest Pain (Circulation 2021;144:e368-e454)",
            review_date=REVIEW_DATE,
            metadata={"chest_pain": cp_presence, "quality": cp_quality, "radiation": cp_radiation},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 2: Chest Pain with Autonomic Warning Signs
    # -------------------------------------------------------------------------
    has_diaphoresis = bool(symptoms.get("diaphoresis", False) or symptoms.get("cold_sweats", False))
    has_nausea = bool(symptoms.get("nausea", False) or symptoms.get("vomiting", False))
    has_acute_dyspnea = bool(symptoms.get("dyspnea", False) or symptoms.get("shortness_of_breath", False))
    
    r2_triggered = cp_presence and (has_diaphoresis or (has_nausea and has_acute_dyspnea))
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_002_CHEST_PAIN_WITH_AUTONOMIC_SIGNS",
            category="emergency",
            title="Chest Pain with Autonomic Neurovegetative Signs",
            triggered=r2_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Chest pain accompanied by unexplained cold sweats (diaphoresis), nausea, "
                "or severe shortness of breath reflects sympathetic overdrive and is a recognized "
                "high-risk hallmark of ongoing transmural myocardial ischemia."
            ),
            action_guidance=(
                "ACTIVATE EMERGENCY RESPONSE (CALL 911) IMMEDIATELY. "
                "Patient requires urgent 12-lead ECG acquisition within 10 minutes of medical contact."
            ),
            guideline_source="ESC 2020 Guidelines for the Management of Acute Coronary Syndromes (Eur Heart J 2021;42:1289-1367)",
            review_date=REVIEW_DATE,
            metadata={"diaphoresis": has_diaphoresis, "nausea": has_nausea, "dyspnea": has_acute_dyspnea},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 3: Acute Severe Rest Dyspnea / Suspected Pulmonary Edema
    # -------------------------------------------------------------------------
    dyspnea_at_rest = bool(symptoms.get("dyspnea_at_rest", False) or symptoms.get("rest_dyspnea", False))
    inability_to_speak = bool(symptoms.get("inability_to_speak_full_sentences", False))
    pink_frothy_sputum = bool(symptoms.get("pink_frothy_sputum", False))

    r3_triggered = (dyspnea_at_rest and inability_to_speak) or pink_frothy_sputum
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_003_ACUTE_PULMONARY_EDEMA",
            category="emergency",
            title="Acute Severe Rest Dyspnea / Suspected Acute Pulmonary Edema",
            triggered=r3_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Acute dyspnea at rest with inability to speak in full sentences or pink frothy sputum "
                "indicates acute respiratory failure, often secondary to acute decompensated heart failure "
                "with pulmonary edema, massive pulmonary embolism, or acute coronary syndrome."
            ),
            action_guidance=(
                "CALL EMERGENCY SERVICES (911) IMMEDIATELY. Position patient sitting upright. "
                "Do not allow patient to lie flat. Administer supplemental oxygen if available."
            ),
            guideline_source="ESC 2021 Guidelines for the Diagnosis and Treatment of Acute and Chronic Heart Failure (Eur Heart J 2021;42:3599-3726)",
            review_date=REVIEW_DATE,
            metadata={"dyspnea_at_rest": dyspnea_at_rest, "inability_to_speak": inability_to_speak, "sputum": pink_frothy_sputum},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 4: Exertional or Unheralded Cardiac Syncope
    # -------------------------------------------------------------------------
    has_syncope = bool(symptoms.get("syncope", False) or symptoms.get("loss_of_consciousness", False))
    syncope_exertional = bool(symptoms.get("syncope_during_exertion", False))
    syncope_with_palpitations = bool(symptoms.get("syncope_preceded_by_palpitations", False) or (has_syncope and symptoms.get("palpitations", False)))
    syncope_supine = bool(symptoms.get("syncope_supine", False))

    r4_triggered = has_syncope and (syncope_exertional or syncope_with_palpitations or syncope_supine)
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_004_CARDIAC_SYNCOPE",
            category="emergency",
            title="High-Risk Cardiac Syncope (Exertional, Arrhythmic, or Supine)",
            triggered=r4_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Syncope occurring during physical exertion, preceded by palpitations, or while supine "
                "is strongly associated with structural heart disease (severe aortic stenosis, hypertrophic cardiomyopathy) "
                "or malignant ventricular arrhythmias, with elevated risk of sudden cardiac death."
            ),
            action_guidance=(
                "CALL 911 / TRANSPORT TO NEAREST EMERGENCY DEPARTMENT IMMEDIATELY. "
                "Patient must be placed on continuous cardiac telemetry and evaluated for life-threatening arrhythmias."
            ),
            guideline_source="2017 ACC/AHA/HRS Guideline for the Evaluation and Management of Patients With Syncope (Circulation 2017;136:e60-e122)",
            review_date=REVIEW_DATE,
            metadata={"syncope": has_syncope, "exertional": syncope_exertional, "supine": syncope_supine},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 5: Hypertensive Crisis / Hypertensive Emergency (Measured Vitals)
    # -------------------------------------------------------------------------
    sbp = vitals.get("systolic_bp") or vitals.get("trestbps")
    dbp = vitals.get("diastolic_bp")

    r5_triggered = False
    r5_rationale = ""
    if sbp is not None or dbp is not None:
        try:
            sbp_val = float(sbp) if sbp is not None else 0.0
            dbp_val = float(dbp) if dbp is not None else 0.0
            is_crisis_numbers = (sbp_val >= 180.0) or (dbp_val >= 120.0)

            # Check for target-organ symptoms (headache, chest pain, vision change, shortness of breath)
            has_organ_symptoms = any(
                bool(symptoms.get(s, False))
                for s in [
                    "chest_pain", "dyspnea", "shortness_of_breath", "severe_headache",
                    "visual_disturbance", "confusion", "neurological_deficit"
                ]
            )

            if is_crisis_numbers and has_organ_symptoms:
                r5_triggered = True
                r5_rationale = (
                    f"Measured BP ({int(sbp_val)}/{int(dbp_val)} mm Hg) meets hypertensive crisis criteria "
                    f"with concurrent acute target-organ symptoms. This represents a Hypertensive Emergency "
                    f"with imminent risk of aortic dissection, acute myocardial infarction, or intracranial hemorrhage."
                )
            elif is_crisis_numbers:
                r5_triggered = True
                r5_rationale = (
                    f"Measured BP ({int(sbp_val)}/{int(dbp_val)} mm Hg) meets hypertensive urgency/crisis criteria "
                    f"(SBP >= 180 or DBP >= 120 mm Hg) requiring immediate emergency medical evaluation."
                )
        except (ValueError, TypeError):
            pass

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_005_HYPERTENSIVE_EMERGENCY",
            category="emergency",
            title="Hypertensive Emergency / Severe Acute Hypertension",
            triggered=r5_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.CLINICAL_MEASUREMENT,
            rationale=r5_rationale or "Measured blood pressure is within acceptable safety parameters.",
            action_guidance=(
                "SEEK IMMEDIATE EMERGENCY MEDICAL CARE. Do not take extra doses of oral antihypertensives "
                "without direct medical supervision. EMS evaluation with parenteral BP titration is indicated."
            ),
            guideline_source="2017 ACC/AHA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults (Hypertension 2018;71:e13-e115)",
            review_date=REVIEW_DATE,
            metadata={"measured_sbp": sbp, "measured_dbp": dbp},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 6: Severe Hypotension / Cardiogenic Shock Physiology (Measured Vitals)
    # -------------------------------------------------------------------------
    r6_triggered = False
    r6_rationale = ""
    if sbp is not None:
        try:
            sbp_val = float(sbp)
            has_hypoperfusion = any(
                bool(symptoms.get(s, False))
                for s in ["dizziness", "confusion", "clammy_skin", "altered_mental_state", "syncope"]
            )
            if sbp_val < 90.0:
                r6_triggered = True
                r6_rationale = (
                    f"Measured systolic BP ({int(sbp_val)} mm Hg) is below 90 mm Hg"
                    + (" with clinical signs of systemic hypoperfusion." if has_hypoperfusion else ".")
                    + " This indicates severe hypotension or decompensated cardiogenic shock."
                )
        except (ValueError, TypeError):
            pass

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_006_CARDIOGENIC_SHOCK_HYPOTENSION",
            category="emergency",
            title="Severe Hypotension / Suspected Cardiogenic Shock",
            triggered=r6_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.CLINICAL_MEASUREMENT,
            rationale=r6_rationale or "Systolic blood pressure is >= 90 mm Hg.",
            action_guidance=(
                "ACTIVATE EMERGENCY MEDICAL SERVICES (911). Keep the patient recumbent with legs slightly "
                "elevated unless pulmonary edema is present. Immediate intravenous support is required."
            ),
            guideline_source="AHA Scientific Statement: Management of Cardiogenic Shock (Circulation 2017;136:e232-e268)",
            review_date=REVIEW_DATE,
            metadata={"measured_sbp": sbp},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 7: Critical Hypoxia / Severe Desaturation (Measured Vitals)
    # -------------------------------------------------------------------------
    spo2 = vitals.get("spo2") or vitals.get("oxygen_saturation")
    r7_triggered = False
    r7_rationale = ""
    if spo2 is not None:
        try:
            spo2_val = float(spo2)
            if spo2_val < 90.0:
                r7_triggered = True
                r7_rationale = (
                    f"Measured pulse oximetry (SpO2 {spo2_val:.1f}%) is below 90% on room air, "
                    f"indicating critical hypoxemia and impending respiratory failure."
                )
        except (ValueError, TypeError):
            pass

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_007_CRITICAL_HYPOXIA",
            category="emergency",
            title="Critical Hypoxemia (SpO2 < 90%)",
            triggered=r7_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.CLINICAL_MEASUREMENT,
            rationale=r7_rationale or "Oxygen saturation is >= 90% or unmeasured.",
            action_guidance=(
                "CALL 911 / EMERGENCY SERVICES. Prompt supplemental oxygen delivery and airway evaluation required."
            ),
            guideline_source="WHO Clinical Management of Acute Respiratory Distress / AHA ACLS Guidelines",
            review_date=REVIEW_DATE,
            metadata={"measured_spo2": spo2},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 8: Hazardous Extremes of Heart Rate (Measured Vitals)
    # -------------------------------------------------------------------------
    hr = vitals.get("heart_rate") or vitals.get("thalch")
    r8_triggered = False
    r8_rationale = ""
    if hr is not None:
        try:
            hr_val = float(hr)
            if hr_val < 40.0:
                r8_triggered = True
                r8_rationale = (
                    f"Measured resting heart rate ({int(hr_val)} bpm) demonstrates severe bradycardia "
                    f"(< 40 bpm) with risk of hemodynamic collapse or high-grade AV block."
                )
            elif hr_val > 150.0:
                r8_triggered = True
                r8_rationale = (
                    f"Measured resting heart rate ({int(hr_val)} bpm) demonstrates severe tachyarrhythmia "
                    f"(> 150 bpm) with risk of hemodynamic compromise or ventricular arrhythmia."
                )
        except (ValueError, TypeError):
            pass

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_008_HAZARDOUS_ARRHYTHMIC_VITALS",
            category="emergency",
            title="Severe Heart Rate Extremes (< 40 bpm or > 150 bpm)",
            triggered=r8_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.CLINICAL_MEASUREMENT,
            rationale=r8_rationale or "Heart rate is within conventional resting range.",
            action_guidance=(
                "SEEK IMMEDIATE EMERGENCY EVALUATION. 12-lead ECG and continuous rhythm monitoring indicated."
            ),
            guideline_source="2018 ACC/AHA/HRS Guideline on the Evaluation and Management of Patients With Bradycardia and Cardiac Conduction Delay",
            review_date=REVIEW_DATE,
            metadata={"measured_heart_rate": hr},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 9: Acute Focal Neurological Deficit (Stroke Signs / FAST)
    # -------------------------------------------------------------------------
    has_facial_droop = bool(symptoms.get("facial_droop", False))
    has_arm_weakness = bool(symptoms.get("arm_weakness", False) or symptoms.get("unilateral_weakness", False))
    has_speech_difficulty = bool(symptoms.get("speech_difficulty", False) or symptoms.get("slurred_speech", False))

    r9_triggered = has_facial_droop or has_arm_weakness or has_speech_difficulty
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="EMERG_009_STROKE_FAST_SIGNS",
            category="emergency",
            title="Acute Stroke Signs (FAST Criteria)",
            triggered=r9_triggered,
            priority=RulePriority.EMERGENCY_IMMEDIATE,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Presence of acute focal neurological deficits (facial droop, unilateral arm weakness, "
                "or speech impairment) represents suspected acute ischemic stroke or intracranial hemorrhage."
            ),
            action_guidance=(
                "CALL 911 / EMS IMMEDIATELY. Note the exact time patient was last seen normal. "
                "Immediate transport to a certified Stroke Center for neuroimaging and thrombolysis evaluation."
            ),
            guideline_source="AHA/ASA Guidelines for the Early Management of Patients With Acute Ischemic Stroke (Stroke 2019;50:e344-e418)",
            review_date=REVIEW_DATE,
            metadata={"facial_droop": has_facial_droop, "arm_weakness": has_arm_weakness, "speech_difficulty": has_speech_difficulty},
        )
    )

    # -------------------------------------------------------------------------
    # Synthesize Emergency Decision & Enforce ML Independence
    # -------------------------------------------------------------------------
    triggered_rules = [r for r in evaluated_rules if r.triggered]
    is_emergency = len(triggered_rules) > 0

    if is_emergency:
        escalation_level = RulePriority.EMERGENCY_IMMEDIATE.value
        action_plan = [r.action_guidance for r in triggered_rules]
    else:
        escalation_level = "NONE"
        action_plan = ["No acute red-flag emergency symptoms or critical vital signs identified."]

    # ML Override Safeguard Audit
    ml_safeguard_message = (
        "SAFEGUARD ACTIVE: Clinical emergency triage operates independently of ML model scores. "
        "Under no circumstances may a statistical prediction de-escalate emergency care."
    )

    if ml_context and is_emergency:
        ml_score = ml_context.get("score") or ml_context.get("calibrated_probability")
        if ml_score is not None and float(ml_score) < 0.5:
            ml_safeguard_message = (
                f"SAFETY OVERRIDE ENFORCED: Machine learning model returned a low predicted score ({ml_score}). "
                f"However, {len(triggered_rules)} red-flag emergency rule(s) triggered. "
                f"Emergency escalation is MANDATORY and cannot be modified by ML predictions."
            )

    return {
        "is_emergency": is_emergency,
        "escalation_level": escalation_level,
        "triggered_count": len(triggered_rules),
        "triggered_rules": [r.to_dict() for r in triggered_rules],
        "all_evaluated_rules": [r.to_dict() for r in evaluated_rules],
        "emergency_action_plan": action_plan,
        "ml_override_safeguard": ml_safeguard_message,
        "clinical_disclaimer": CLINICAL_SAFETY_DISCLAIMER,
    }
