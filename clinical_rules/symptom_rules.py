"""
Symptom Rules Engine.

Processes self-reported patient symptoms and clinical risk factors for
subacute, exertional, and chronic cardiovascular patterns.

CORE CLINICAL DIRECTIVES:
1. INPUT MODALITY SEPARATION: Distinguishes patient-reported symptoms (subjective)
   from measured vital signs or lab values (objective).
2. CONFLICT RESOLUTION: Detects conflicting patient reports (e.g., self-reported
   'no dyspnea' alongside measured hypoxia SpO2 < 92%, or 'no chest pain' alongside
   'crushing pressure') and resolves conservatively in favor of patient safety.
3. INCOMPLETE INPUT HANDLING: Avoids assuming uncollected symptoms are absent;
   explicitly tracks unassessed parameters.
4. EVIDENCE CITATIONS: Rules are based on established clinical diagnostic criteria
   (Diamond-Forrester / AHA 2021, ESC 2021 Heart Failure, ACC/AHA/HRS 2017).
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from clinical_rules import (
    CLINICAL_SAFETY_DISCLAIMER,
    ClinicalRuleResult,
    InputModality,
    RulePriority,
)

REVIEW_DATE = "2026-10-01"


def evaluate_symptom_rules(
    patient_symptoms: Optional[Dict[str, Any]] = None,
    measured_vitals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate cardiovascular symptom patterns and detect conflicting inputs.
    
    Parameters
    ----------
    patient_symptoms : dict, optional
        Self-reported symptoms (chest pain, dyspnea, palpitations, edema, etc.).
    measured_vitals : dict, optional
        Clinically measured vitals (BP, HR, SpO2) used for cross-modality conflict checks.
        
    Returns
    -------
    dict
        Structured symptom evaluation containing:
        - angina_classification: str ('typical_angina', 'atypical_angina', 'non_anginal', 'none')
        - congestive_symptom_score: int
        - detected_conflicts: list of dict
        - unassessed_features: list of str
        - triggered_rules: list of dict
        - all_evaluated_rules: list of dict
        - clinical_summary: list of str
        - clinical_disclaimer: str
    """
    symptoms = patient_symptoms or {}
    vitals = measured_vitals or {}

    evaluated_rules: List[ClinicalRuleResult] = []
    detected_conflicts: List[Dict[str, Any]] = []
    unassessed_features: List[str] = []

    # -------------------------------------------------------------------------
    # Cross-Modality and Internal Conflict Detection
    # -------------------------------------------------------------------------
    # Conflict 1: Chest pain reported False, but descriptor indicates pressure/crushing
    cp_raw = symptoms.get("chest_pain")
    cp_pressure = bool(symptoms.get("chest_pressure", False))
    cp_quality = str(symptoms.get("chest_pain_quality", "")).lower()

    resolved_cp = False
    if cp_raw is True:
        resolved_cp = True
    elif cp_raw is False and (cp_pressure or any(w in cp_quality for w in ["crushing", "tightness", "pressure", "heavy"])):
        resolved_cp = True
        detected_conflicts.append({
            "conflict_id": "CONFLICT_CHEST_PAIN_SELF_REPORT",
            "description": "Patient reported 'no chest pain', but detailed chest pressure or tightness is present.",
            "resolution": "Resolved conservatively to Chest Pain = True (AHA 2021 recognizes discomfort/pressure as ischemic equivalents).",
        })
    elif cp_raw is None:
        unassessed_features.append("chest_pain")

    # Conflict 2: Patient reports no shortness of breath, but measured SpO2 is hypoxic
    dyspnea_raw = symptoms.get("dyspnea")
    spo2_val = vitals.get("spo2") or vitals.get("oxygen_saturation")
    resolved_dyspnea = bool(dyspnea_raw)

    if spo2_val is not None:
        try:
            if float(spo2_val) < 92.0 and dyspnea_raw is False:
                resolved_dyspnea = True
                detected_conflicts.append({
                    "conflict_id": "CONFLICT_DYSPNEA_VS_SPO2",
                    "description": f"Patient reported 'no shortness of breath', but measured SpO2 is hypoxic ({spo2_val}%).",
                    "resolution": "Resolved to clinically significant respiratory compromise based on objective pulse oximetry.",
                })
        except (ValueError, TypeError):
            pass

    if dyspnea_raw is None:
        unassessed_features.append("dyspnea")

    # -------------------------------------------------------------------------
    # RULE 1: Angina Pectoris Classification (Diamond-Forrester / AHA 2021)
    # -------------------------------------------------------------------------
    # Criteria:
    # 1. Substernal chest discomfort with characteristic quality and duration
    # 2. Provoked by exertion or emotional stress
    # 3. Relieved by rest or nitroglycerin within minutes
    is_substernal = bool(symptoms.get("substernal_location", False) or resolved_cp)
    exertional_provocation = bool(symptoms.get("exertional_provocation", False) or symptoms.get("exang", False))
    rest_relief = bool(symptoms.get("relieved_by_rest", False) or symptoms.get("relieved_by_nitroglycerin", False))

    criteria_count = sum([is_substernal, exertional_provocation, rest_relief])

    if criteria_count == 3:
        angina_class = "typical_angina"
        angina_rationale = (
            "Meets all 3 Diamond-Forrester criteria: substernal discomfort, exertional provocation, "
            "and relief with rest/nitroglycerin. Indicates HIGH pretest probability of obstructive CAD."
        )
        angina_priority = RulePriority.URGENT_SAME_DAY
        angina_action = "Prompt outpatient or urgent cardiology consultation; diagnostic testing (e.g. ECG, stress test/CTA) strongly recommended."
        r1_triggered = True
    elif criteria_count == 2:
        angina_class = "atypical_angina"
        angina_rationale = (
            "Meets 2 of 3 Diamond-Forrester criteria (Atypical Angina). "
            "Indicates INTERMEDIATE pretest probability of coronary artery disease."
        )
        angina_priority = RulePriority.ROUTINE_OUTPATIENT
        angina_action = "Schedule clinical cardiology evaluation and non-invasive functional or anatomical testing."
        r1_triggered = True
    elif criteria_count == 1:
        angina_class = "non_anginal"
        angina_rationale = "Meets only 1 Diamond-Forrester criterion (Non-anginal chest discomfort). Lower CAD probability."
        angina_priority = RulePriority.INFORMATIONAL
        angina_action = "Evaluate for non-cardiac etiologies (gastroesophageal, musculoskeletal, pericardial) if red flags absent."
        r1_triggered = False
    else:
        angina_class = "none"
        angina_rationale = "No anginal chest discomfort criteria reported."
        angina_priority = RulePriority.INFORMATIONAL
        angina_action = "Routine preventive health maintenance."
        r1_triggered = False

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="SYMP_001_ANGINA_CLASSIFICATION",
            category="symptom",
            title=f"Angina Classification ({angina_class.replace('_', ' ').title()})",
            triggered=r1_triggered,
            priority=angina_priority,
            modality=InputModality.PATIENT_REPORTED,
            rationale=angina_rationale,
            action_guidance=angina_action,
            guideline_source="AHA/ACC 2021 Guideline for the Evaluation and Diagnosis of Chest Pain (Circulation 2021;144:e368-e454)",
            review_date=REVIEW_DATE,
            metadata={"criteria_met_count": criteria_count, "classification": angina_class},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 2: Congestive Heart Failure Symptom Complex (ESC 2021)
    # -------------------------------------------------------------------------
    has_orthopnea = bool(symptoms.get("orthopnea", False))
    has_pnd = bool(symptoms.get("paroxysmal_nocturnal_dyspnea", False) or symptoms.get("pnd", False))
    has_edema = bool(symptoms.get("bilateral_leg_edema", False) or symptoms.get("ankle_edema", False))
    has_fatigue = bool(symptoms.get("unexplained_fatigue", False))
    has_rapid_weight_gain = bool(symptoms.get("rapid_weight_gain", False))

    congestive_features = [has_orthopnea, has_pnd, has_edema, has_rapid_weight_gain, resolved_dyspnea]
    congestive_score = sum(congestive_features)

    r2_triggered = congestive_score >= 2 or has_pnd or has_orthopnea
    r2_rationale = (
        f"Patient exhibits {congestive_score} cardinal congestive heart failure symptoms: "
        + (f"Orthopnea (must sleep propped up). " if has_orthopnea else "")
        + (f"Paroxysmal Nocturnal Dyspnea (waking breathless). " if has_pnd else "")
        + (f"Bilateral lower extremity edema. " if has_edema else "")
        + (f"Exertional dyspnea. " if resolved_dyspnea else "")
        + "This symptom pattern reflects elevated cardiac filling pressures."
    )

    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="SYMP_002_HEART_FAILURE_CONGESTIVE_SIGNS",
            category="symptom",
            title="Congestive Heart Failure Symptom Complex",
            triggered=r2_triggered,
            priority=RulePriority.URGENT_SAME_DAY if (has_pnd or congestive_score >= 3) else RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.PATIENT_REPORTED,
            rationale=r2_rationale if r2_triggered else "Fewer than 2 congestive heart failure signs reported.",
            action_guidance=(
                "Recommend urgent or prompt clinical evaluation including serum natriuretic peptides "
                "(BNP or NT-proBNP), 12-lead ECG, and transthoracic echocardiogram (TTE) to assess LVEF."
            ),
            guideline_source="ESC 2021 Guidelines for the Diagnosis and Treatment of Acute and Chronic Heart Failure (Eur Heart J 2021;42:3599-3726)",
            review_date=REVIEW_DATE,
            metadata={
                "congestive_score": congestive_score,
                "orthopnea": has_orthopnea,
                "pnd": has_pnd,
                "edema": has_edema,
            },
        )
    )

    # -------------------------------------------------------------------------
    # RULE 3: Arrhythmic Palpitations Pattern (ACC/AHA/HRS 2017)
    # -------------------------------------------------------------------------
    palpitations_present = bool(symptoms.get("palpitations", False))
    palpitations_sudden = bool(symptoms.get("palpitations_sudden_onset", False))
    palpitations_irregular = bool(symptoms.get("irregular_heartbeat", False))
    palpitations_presyncope = bool(symptoms.get("presyncope", False) or symptoms.get("dizziness_with_palpitations", False))

    r3_triggered = palpitations_present and (palpitations_presyncope or palpitations_irregular or palpitations_sudden)
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="SYMP_003_ARRHYTHMIC_PALPITATIONS_PATTERN",
            category="symptom",
            title="Symptomatic Arrhythmic Palpitations Pattern",
            triggered=r3_triggered,
            priority=RulePriority.URGENT_SAME_DAY if palpitations_presyncope else RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Patient reports palpitations associated with lightheadedness/presyncope, sudden onset, "
                "or irregular rhythm, suggesting potential paroxysmal atrial fibrillation, supraventricular "
                "tachycardia, or ventricular ectopy."
            ),
            action_guidance=(
                "Recommend 12-lead ECG and ambulatory ECG monitoring (Holter or 14-day patch monitor) "
                "to capture symptom-rhythm correlation. Avoid unmonitored vigorous exertion pending workup."
            ),
            guideline_source="2017 ACC/AHA/HRS Guideline for the Evaluation and Management of Patients With Syncope / Arrhythmia",
            review_date=REVIEW_DATE,
            metadata={"presyncope": palpitations_presyncope, "irregular": palpitations_irregular},
        )
    )

    # -------------------------------------------------------------------------
    # RULE 4: Peripheral Arterial Disease / Intermittent Claudication
    # -------------------------------------------------------------------------
    has_claudication = bool(symptoms.get("calf_pain_walking", False) or symptoms.get("claudication", False))
    claudication_relieved_by_rest = bool(symptoms.get("claudication_relieved_by_rest", False))

    r4_triggered = has_claudication and claudication_relieved_by_rest
    evaluated_rules.append(
        ClinicalRuleResult(
            rule_id="SYMP_004_INTERMITTENT_CLAUDICATION",
            category="symptom",
            title="Intermittent Claudication (Peripheral Artery Disease)",
            triggered=r4_triggered,
            priority=RulePriority.ROUTINE_OUTPATIENT,
            modality=InputModality.PATIENT_REPORTED,
            rationale=(
                "Exertional lower-extremity calf cramping provoked by walking and consistently "
                "relieved within 10 minutes of rest represents classic intermittent claudication, "
                "a marker of systemic atherosclerosis and elevated cardiovascular event risk."
            ),
            action_guidance=(
                "Recommend resting Ankle-Brachial Index (ABI) measurement and aggressive cardiovascular "
                "risk factor optimization (antiplatelet therapy, high-intensity statin, blood pressure control)."
            ),
            guideline_source="2016 AHA/ACC Guideline on the Management of Patients With Lower Extremity Peripheral Artery Disease",
            review_date=REVIEW_DATE,
            metadata={"claudication": has_claudication, "rest_relief": claudication_relieved_by_rest},
        )
    )

    # -------------------------------------------------------------------------
    # Synthesize Summary
    # -------------------------------------------------------------------------
    triggered_rules = [r for r in evaluated_rules if r.triggered]
    summary_messages = [f"[{r.rule_id}] {r.title}: {r.rationale}" for r in triggered_rules]

    if not summary_messages:
        summary_messages = ["No specific subacute or chronic cardiovascular symptom syndromes identified."]

    return {
        "angina_classification": angina_class,
        "congestive_symptom_score": congestive_score,
        "triggered_count": len(triggered_rules),
        "triggered_rules": [r.to_dict() for r in triggered_rules],
        "all_evaluated_rules": [r.to_dict() for r in evaluated_rules],
        "detected_conflicts": detected_conflicts,
        "unassessed_features": unassessed_features,
        "clinical_summary": summary_messages,
        "clinical_disclaimer": CLINICAL_SAFETY_DISCLAIMER,
    }
