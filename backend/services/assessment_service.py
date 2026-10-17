"""
Clinical Assessment, Symptom, and Vital Sign Management Service.

CRITICAL RULES:
1. Every vital sign is strictly nullable with NO default values.
2. Missing measurements are stored as SQL NULL, never as 0.0.
3. Automatically computes BMI if height and weight are provided and BMI is not specified.
4. Leverages Diamond-Forrester and congestive symptom rules to classify angina and compute score.
"""

from typing import Any, Dict, Optional
from backend.extensions import db
from backend.schemas.symptom_schema import (
    AssessmentUpdateSchema,
    PatientSymptomSchema,
    VitalSignSchema,
)
from database.models import Assessment, PatientSymptom, VitalSign
from clinical_rules.symptom_rules import evaluate_symptom_rules


class AssessmentService:
    """Manages assessment encounters, symptoms, and physiological vitals."""

    @staticmethod
    def get_assessment(assessment_id: int) -> Optional[Assessment]:
        """Fetch assessment by primary key ID."""
        return Assessment.query.filter_by(id=assessment_id).first()

    @classmethod
    def update_assessment(
        cls,
        assessment_id: int,
        data: AssessmentUpdateSchema,
    ) -> Optional[Assessment]:
        """Update assessment status, visit reason, notes, or emergency escalation level."""
        assessment = cls.get_assessment(assessment_id)
        if not assessment:
            return None

        if data.status is not None:
            assessment.status = data.status
        if data.reason_for_visit is not None:
            assessment.reason_for_visit = data.reason_for_visit
        if data.clinical_notes is not None:
            assessment.clinical_notes = data.clinical_notes
        if data.emergency_escalation_level is not None:
            assessment.emergency_escalation_level = data.emergency_escalation_level

        db.session.commit()
        return assessment

    @classmethod
    def get_or_create_symptoms(cls, assessment_id: int) -> Optional[PatientSymptom]:
        """Retrieve existing symptoms or create a blank record for the encounter."""
        assessment = cls.get_assessment(assessment_id)
        if not assessment:
            return None

        symptom_record = PatientSymptom.query.filter_by(assessment_id=assessment_id).first()
        if not symptom_record:
            symptom_record = PatientSymptom(assessment_id=assessment_id)
            db.session.add(symptom_record)
            db.session.commit()
        return symptom_record

    @classmethod
    def save_symptoms(
        cls,
        assessment_id: int,
        data: PatientSymptomSchema,
    ) -> Optional[PatientSymptom]:
        """Save or update patient-reported symptoms, running clinical pattern classification."""
        assessment = cls.get_assessment(assessment_id)
        if not assessment:
            return None

        symptom_record = PatientSymptom.query.filter_by(assessment_id=assessment_id).first()
        if not symptom_record:
            symptom_record = PatientSymptom(assessment_id=assessment_id)
            db.session.add(symptom_record)

        # Update symptoms only if explicitly set in schema
        dumped = data.model_dump(exclude_unset=True)
        for key, val in dumped.items():
            if hasattr(symptom_record, key):
                setattr(symptom_record, key, val)

        # Build current symptom dictionary for rule evaluation
        current_symptoms = {
            "chest_pain": symptom_record.chest_pain,
            "chest_pain_quality": symptom_record.chest_pain_quality,
            "substernal_location": symptom_record.substernal_location,
            "exertional_provocation": symptom_record.exertional_provocation,
            "relieved_by_rest": symptom_record.relieved_by_rest,
            "dyspnea": symptom_record.dyspnea,
            "dyspnea_at_rest": symptom_record.dyspnea_at_rest,
            "orthopnea": symptom_record.orthopnea,
            "paroxysmal_nocturnal_dyspnea": symptom_record.paroxysmal_nocturnal_dyspnea,
            "palpitations": symptom_record.palpitations,
            "syncope": symptom_record.syncope,
            "syncope_during_exertion": symptom_record.syncope_during_exertion,
            "diaphoresis": symptom_record.diaphoresis,
            "bilateral_leg_edema": symptom_record.bilateral_leg_edema,
        }

        # Run clinical symptom rules to compute Diamond-Forrester and congestive scores
        eval_result = evaluate_symptom_rules(patient_symptoms=current_symptoms)
        if not data.angina_classification:
            symptom_record.angina_classification = eval_result.get("angina_classification")
        if data.congestive_score is None:
            symptom_record.congestive_score = eval_result.get("congestive_symptom_score")

        db.session.commit()
        return symptom_record

    @classmethod
    def get_or_create_vitals(cls, assessment_id: int) -> Optional[VitalSign]:
        """Retrieve existing vitals or create an empty record for the encounter."""
        assessment = cls.get_assessment(assessment_id)
        if not assessment:
            return None

        vitals_record = VitalSign.query.filter_by(assessment_id=assessment_id).first()
        if not vitals_record:
            vitals_record = VitalSign(assessment_id=assessment_id)
            db.session.add(vitals_record)
            db.session.commit()
        return vitals_record

    @classmethod
    def save_vitals(
        cls,
        assessment_id: int,
        data: VitalSignSchema,
    ) -> Optional[VitalSign]:
        """
        Save or update clinically measured vitals.
        Strictly preserves NULL values for unmeasured metrics. Never assigns 0.0 defaults.
        """
        assessment = cls.get_assessment(assessment_id)
        if not assessment:
            return None

        vitals_record = VitalSign.query.filter_by(assessment_id=assessment_id).first()
        if not vitals_record:
            vitals_record = VitalSign(assessment_id=assessment_id)
            db.session.add(vitals_record)

        dumped = data.model_dump(exclude_unset=True)
        for key, val in dumped.items():
            if hasattr(vitals_record, key):
                setattr(vitals_record, key, val)

        # Automatically calculate BMI if height and weight are provided and BMI is not set
        if vitals_record.height_cm and vitals_record.weight_kg and vitals_record.bmi is None:
            try:
                height_m = vitals_record.height_cm / 100.0
                if height_m > 0:
                    vitals_record.bmi = round(vitals_record.weight_kg / (height_m ** 2), 2)
            except Exception:
                pass

        db.session.commit()
        return vitals_record
