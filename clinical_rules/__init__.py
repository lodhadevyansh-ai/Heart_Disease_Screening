"""
Clinical Rules Module.

Contains rule-based engines for:
1. Emergency Triage and Red-Flag Safety Rules (independent of ML predictions).
2. Symptom Evaluation and Cardiovascular Risk Pattern Processing.
3. Evidence-Based Secondary Diagnostic Test Recommendations.

CRITICAL CLINICAL DIRECTIVE:
These rules are research and educational prototypes based on published international
clinical practice guidelines (AHA/ACC, ESC, NICE). They do NOT constitute medical
advice, autonomous diagnostic determinations, or formal regulatory-approved SaMD.
Emergency presentations must ALWAYS trigger immediate emergency medical services (911/EMS).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Global prototype safety disclaimer
CLINICAL_SAFETY_DISCLAIMER = (
    "This clinical safety and recommendation engine is a research and educational prototype. "
    "It has NOT undergone formal regulatory review (e.g., FDA 510(k), CE-mark Software as a Medical Device). "
    "It does NOT replace professional clinical judgment, emergency medical services, or formal diagnostic workup. "
    "If a patient is experiencing life-threatening symptoms, immediately contact emergency services (911/112/EMS)."
)


class RulePriority(str, Enum):
    """Clinical priority tiers for rule evaluations."""
    EMERGENCY_IMMEDIATE = "EMERGENCY_IMMEDIATE_911"
    URGENT_SAME_DAY = "URGENT_SAME_DAY"
    ROUTINE_OUTPATIENT = "ROUTINE_OUTPATIENT"
    INFORMATIONAL = "INFORMATIONAL"


class InputModality(str, Enum):
    """Distinction between patient-reported symptoms and measured physiological metrics."""
    PATIENT_REPORTED = "patient_reported_symptom"
    CLINICAL_MEASUREMENT = "clinical_measurement_vital"
    COMBINED_ASSESSMENT = "combined_assessment"


@dataclass
class ClinicalRuleResult:
    """
    Structured, testable representation of a clinical rule evaluation.
    
    Attributes
    ----------
    rule_id : str
        Unique rule code (e.g. 'EMERG_001_ACUTE_CHEST_PAIN').
    category : str
        Rule category: 'emergency', 'symptom', or 'recommendation'.
    title : str
        Human-readable clinical rule name.
    triggered : bool
        Whether the clinical condition or threshold was met.
    priority : RulePriority
        Severity/urgency level.
    modality : InputModality
        Source modality (patient-reported vs measured vital).
    rationale : str
        Clinical rationale explaining why the rule triggered.
    action_guidance : str
        Actionable instruction for the patient or provider.
    guideline_source : str
        Primary published guideline citation.
    review_date : str
        Clinical review audit date (YYYY-MM-DD).
    metadata : dict
        Additional parameters, measured values, or triggering keys.
    """
    rule_id: str
    category: str
    title: str
    triggered: bool
    priority: RulePriority
    modality: InputModality
    rationale: str
    action_guidance: str
    guideline_source: str
    review_date: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "title": self.title,
            "triggered": self.triggered,
            "priority": self.priority.value if hasattr(self.priority, "value") else str(self.priority),
            "modality": self.modality.value if hasattr(self.modality, "value") else str(self.modality),
            "rationale": self.rationale,
            "action_guidance": self.action_guidance,
            "guideline_source": self.guideline_source,
            "review_date": self.review_date,
            "metadata": self.metadata,
        }


from clinical_rules.emergency_rules import evaluate_emergency_rules
from clinical_rules.symptom_rules import evaluate_symptom_rules
from clinical_rules.test_recommendations import generate_test_recommendations


def evaluate_clinical_safety(
    patient_symptoms: Optional[Dict[str, Any]] = None,
    measured_vitals: Optional[Dict[str, Any]] = None,
    clinical_history: Optional[Dict[str, Any]] = None,
    ml_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for comprehensive clinical rule evaluation.
    
    Coordinates emergency safety triage, symptom characterization, and evidence-based
    test recommendations, enforcing emergency primacy over routine workflows.
    
    Parameters
    ----------
    patient_symptoms : dict, optional
        Self-reported symptoms.
    measured_vitals : dict, optional
        Clinically measured physiological metrics.
    clinical_history : dict, optional
        Past medical history, age, sex, risk factors.
    ml_context : dict, optional
        Machine learning predictions (used strictly for override safeguards).
        
    Returns
    -------
    dict
        Consolidated clinical decision support payload.
    """
    emergency_res = evaluate_emergency_rules(
        patient_symptoms=patient_symptoms,
        measured_vitals=measured_vitals,
        ml_context=ml_context,
    )

    symptom_res = evaluate_symptom_rules(
        patient_symptoms=patient_symptoms,
        measured_vitals=measured_vitals,
    )

    recommendation_res = generate_test_recommendations(
        patient_symptoms=patient_symptoms,
        measured_vitals=measured_vitals,
        clinical_history=clinical_history,
        symptom_eval=symptom_res,
    )

    is_emergency = emergency_res["is_emergency"]
    overall_urgency = (
        RulePriority.EMERGENCY_IMMEDIATE.value
        if is_emergency
        else (
            RulePriority.URGENT_SAME_DAY.value
            if any(r["priority"] == RulePriority.URGENT_SAME_DAY.value for r in symptom_res["triggered_rules"])
            else RulePriority.ROUTINE_OUTPATIENT.value
        )
    )

    return {
        "status": "success",
        "is_emergency": is_emergency,
        "overall_urgency": overall_urgency,
        "emergency_triage": emergency_res,
        "symptom_evaluation": symptom_res,
        "diagnostic_recommendations": recommendation_res,
        "clinical_safety_notice": (
            "EMERGENCY PRIMACY: Red-flag emergency rules supersede all other recommendations and ML predictions. "
            "If an emergency rule triggered, emergency medical services must be contacted immediately."
            if is_emergency
            else "No red-flag emergency symptoms or critical vital signs identified."
        ),
        "disclaimer": CLINICAL_SAFETY_DISCLAIMER,
    }


__all__ = [
    "CLINICAL_SAFETY_DISCLAIMER",
    "RulePriority",
    "InputModality",
    "ClinicalRuleResult",
    "evaluate_emergency_rules",
    "evaluate_symptom_rules",
    "generate_test_recommendations",
    "evaluate_clinical_safety",
]

