"""
Clinical Safety and Recommendation Service.

Coordinates emergency rule triage, symptom processing, and evidence-based
secondary test recommendations. Enforces emergency primacy over routine and ML workflows.
"""

from typing import Any, Dict, Optional

from backend.extensions import db
from clinical_rules import RulePriority, evaluate_clinical_safety
from database.models import Assessment


class RecommendationService:
    """Service evaluating clinical safety rules and evidence-based recommendations."""

    @staticmethod
    def evaluate_ad_hoc(
        patient_symptoms: Optional[Dict[str, Any]] = None,
        measured_vitals: Optional[Dict[str, Any]] = None,
        clinical_history: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate clinical rules against ad-hoc input payloads."""
        return evaluate_clinical_safety(
            patient_symptoms=patient_symptoms,
            measured_vitals=measured_vitals,
            clinical_history=clinical_history,
        )

    @staticmethod
    def evaluate_assessment(assessment_id: int) -> Optional[Dict[str, Any]]:
        """
        Evaluate clinical rules for an existing clinical assessment encounter.
        Extracts stored symptoms, vitals, and patient demographics.
        Automatically updates assessment emergency level if emergency rules trigger.
        """
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            return None

        # Assemble symptom dictionary
        patient_symptoms: Dict[str, Any] = {}
        if assessment.symptoms:
            s = assessment.symptoms
            patient_symptoms = {
                "chest_pain": s.chest_pain,
                "chest_pain_quality": s.chest_pain_quality,
                "chest_pain_radiation": s.chest_pain_radiation,
                "substernal_location": s.substernal_location,
                "exertional_provocation": s.exertional_provocation,
                "relieved_by_rest": s.relieved_by_rest,
                "dyspnea": s.dyspnea,
                "dyspnea_at_rest": s.dyspnea_at_rest,
                "orthopnea": s.orthopnea,
                "paroxysmal_nocturnal_dyspnea": s.paroxysmal_nocturnal_dyspnea,
                "palpitations": s.palpitations,
                "syncope": s.syncope,
                "syncope_during_exertion": s.syncope_during_exertion,
                "diaphoresis": s.diaphoresis,
                "bilateral_leg_edema": s.bilateral_leg_edema,
                "angina_classification": s.angina_classification,
            }

        # Assemble vitals dictionary
        measured_vitals: Dict[str, Any] = {}
        if assessment.vitals:
            v = assessment.vitals
            measured_vitals = {
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "heart_rate": v.heart_rate,
                "respiratory_rate": v.respiratory_rate,
                "spo2": v.spo2,
                "temperature_celsius": v.temperature_celsius,
                "bmi": v.bmi,
            }

        # Assemble patient clinical history
        clinical_history: Dict[str, Any] = {}
        if assessment.patient:
            p = assessment.patient
            clinical_history = {
                "age": p.age,
                "sex": p.sex,
            }

        # Extract latest prediction context if available
        ml_context: Dict[str, Any] = {}
        if assessment.predictions:
            latest_pred = assessment.predictions[-1]
            ml_context = {
                "task_name": latest_pred.task_name,
                "predicted_risk_level": "low" if (latest_pred.calibrated_probability or 0) < 0.2 else "high",
                "risk_score": latest_pred.calibrated_probability or latest_pred.raw_score,
            }

        # Execute unified clinical safety evaluation
        result = evaluate_clinical_safety(
            patient_symptoms=patient_symptoms,
            measured_vitals=measured_vitals,
            clinical_history=clinical_history,
            ml_context=ml_context,
        )

        # If red-flag emergency triggered, escalate assessment status
        if result["is_emergency"]:
            assessment.emergency_escalation_level = RulePriority.EMERGENCY_IMMEDIATE.value
            assessment.status = "flagged_emergency"
            db.session.commit()
        elif assessment.emergency_escalation_level == RulePriority.EMERGENCY_IMMEDIATE.value:
            # Keep emergency escalation if previously flagged
            pass

        return result
