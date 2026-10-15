"""
Comprehensive Unit Tests for Clinical Safety, Emergency Triage, and Recommendation Rules.

Tests cover:
1. Emergency red-flag rules (ACS, autonomic signs, pulmonary edema, syncope, FAST stroke).
2. Critical vital sign emergencies (hypertensive crisis, shock hypotension, severe hypoxia, HR extremes).
3. Machine Learning independence (low ML score cannot de-escalate emergency triage).
4. Incomplete inputs handling (no crashes, clean unassessed tracking).
5. Conflicting inputs resolution (subjective report vs objective vitals, conservative clinical resolution).
6. Non-urgent, routine presentations.
7. Structured rule result contracts (rule_id, rationale, priority, guideline_source, review_date).
8. Evidence-based secondary diagnostic test recommendations.
"""

import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clinical_rules import (
    CLINICAL_SAFETY_DISCLAIMER,
    RulePriority,
    InputModality,
    ClinicalRuleResult,
    evaluate_emergency_rules,
    evaluate_symptom_rules,
    generate_test_recommendations,
    evaluate_clinical_safety,
)


class TestEmergencyRules:
    """Test suite for emergency triage and red-flag safety rules."""

    def test_acute_ischemic_chest_pain_triggers_emergency(self):
        symptoms = {
            "chest_pain": True,
            "chest_pain_quality": "crushing pressure",
            "chest_pain_radiation": "left arm and jaw",
        }
        res = evaluate_emergency_rules(patient_symptoms=symptoms)
        assert res["is_emergency"] is True
        assert res["escalation_level"] == RulePriority.EMERGENCY_IMMEDIATE.value

        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_001_ACUTE_CORONARY_SYNDROME" in rule_ids

        # Check structured schema
        r1 = next(r for r in res["triggered_rules"] if r["rule_id"] == "EMERG_001_ACUTE_CORONARY_SYNDROME")
        assert r1["priority"] == RulePriority.EMERGENCY_IMMEDIATE.value
        assert "AHA/ACC 2021" in r1["guideline_source"]
        assert r1["review_date"] == "2026-10-01"
        assert "911" in r1["action_guidance"]

    def test_chest_pain_with_autonomic_signs(self):
        symptoms = {
            "chest_pain": True,
            "diaphoresis": True,
            "nausea": True,
        }
        res = evaluate_emergency_rules(patient_symptoms=symptoms)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_002_CHEST_PAIN_WITH_AUTONOMIC_SIGNS" in rule_ids

    def test_acute_pulmonary_edema_dyspnea(self):
        symptoms = {
            "dyspnea_at_rest": True,
            "inability_to_speak_full_sentences": True,
            "pink_frothy_sputum": True,
        }
        res = evaluate_emergency_rules(patient_symptoms=symptoms)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_003_ACUTE_PULMONARY_EDEMA" in rule_ids

    def test_exertional_cardiac_syncope(self):
        symptoms = {
            "syncope": True,
            "syncope_during_exertion": True,
        }
        res = evaluate_emergency_rules(patient_symptoms=symptoms)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_004_CARDIAC_SYNCOPE" in rule_ids

    def test_hypertensive_emergency(self):
        vitals = {"systolic_bp": 195.0, "diastolic_bp": 125.0}
        symptoms = {"chest_pain": True, "severe_headache": True}
        res = evaluate_emergency_rules(patient_symptoms=symptoms, measured_vitals=vitals)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_005_HYPERTENSIVE_EMERGENCY" in rule_ids

    def test_cardiogenic_shock_hypotension(self):
        vitals = {"systolic_bp": 78.0}
        symptoms = {"dizziness": True, "clammy_skin": True}
        res = evaluate_emergency_rules(patient_symptoms=symptoms, measured_vitals=vitals)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_006_CARDIOGENIC_SHOCK_HYPOTENSION" in rule_ids

    def test_critical_hypoxia(self):
        vitals = {"spo2": 84.0}
        res = evaluate_emergency_rules(measured_vitals=vitals)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_007_CRITICAL_HYPOXIA" in rule_ids

    def test_severe_bradycardia_and_tachycardia(self):
        # Bradycardia < 40 bpm
        res_brady = evaluate_emergency_rules(measured_vitals={"heart_rate": 32.0})
        assert res_brady["is_emergency"] is True
        assert any(r["rule_id"] == "EMERG_008_HAZARDOUS_ARRHYTHMIC_VITALS" for r in res_brady["triggered_rules"])

        # Tachycardia > 150 bpm
        res_tachy = evaluate_emergency_rules(measured_vitals={"heart_rate": 168.0})
        assert res_tachy["is_emergency"] is True
        assert any(r["rule_id"] == "EMERG_008_HAZARDOUS_ARRHYTHMIC_VITALS" for r in res_tachy["triggered_rules"])

    def test_stroke_fast_signs(self):
        symptoms = {"facial_droop": True, "arm_weakness": True}
        res = evaluate_emergency_rules(patient_symptoms=symptoms)
        assert res["is_emergency"] is True
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "EMERG_009_STROKE_FAST_SIGNS" in rule_ids

    def test_ml_score_cannot_override_or_deescalate_emergency(self):
        # Patient has crushing chest pain with radiation (red flag)
        symptoms = {
            "chest_pain": True,
            "chest_pain_quality": "crushing pressure",
            "chest_pain_radiation": "left arm",
        }
        # Model predicted very low probability
        ml_context = {
            "score": 0.04,
            "calibrated_probability": 0.04,
            "predicted_class_id": 0,
            "task": "coronary_artery_disease",
        }

        res = evaluate_emergency_rules(patient_symptoms=symptoms, ml_context=ml_context)
        # Emergency status MUST remain active
        assert res["is_emergency"] is True
        assert res["escalation_level"] == RulePriority.EMERGENCY_IMMEDIATE.value
        # Safeguard notice must document that low ML prediction was rejected
        assert "SAFETY OVERRIDE ENFORCED" in res["ml_override_safeguard"]
        assert "0.04" in res["ml_override_safeguard"]


class TestSymptomRulesAndConflictResolution:
    """Test suite for symptom processing, Diamond-Forrester classification, and conflicts."""

    def test_typical_angina_diamond_forrester(self):
        symptoms = {
            "chest_pain": True,
            "substernal_location": True,
            "exertional_provocation": True,
            "relieved_by_rest": True,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert res["angina_classification"] == "typical_angina"
        r1 = next(r for r in res["triggered_rules"] if r["rule_id"] == "SYMP_001_ANGINA_CLASSIFICATION")
        assert r1["priority"] == RulePriority.URGENT_SAME_DAY.value
        assert "Diamond-Forrester" in r1["rationale"]

    def test_atypical_angina_diamond_forrester(self):
        symptoms = {
            "chest_pain": True,
            "substernal_location": True,
            "exertional_provocation": True,
            "relieved_by_rest": False,  # Only 2 criteria met
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert res["angina_classification"] == "atypical_angina"

    def test_congestive_heart_failure_signs(self):
        symptoms = {
            "orthopnea": True,
            "paroxysmal_nocturnal_dyspnea": True,
            "bilateral_leg_edema": True,
            "dyspnea": True,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert res["congestive_symptom_score"] >= 3
        rule_ids = [r["rule_id"] for r in res["triggered_rules"]]
        assert "SYMP_002_HEART_FAILURE_CONGESTIVE_SIGNS" in rule_ids

    def test_arrhythmic_palpitations_pattern(self):
        symptoms = {
            "palpitations": True,
            "irregular_heartbeat": True,
            "presyncope": True,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert any(r["rule_id"] == "SYMP_003_ARRHYTHMIC_PALPITATIONS_PATTERN" for r in res["triggered_rules"])

    def test_intermittent_claudication_pad(self):
        symptoms = {
            "calf_pain_walking": True,
            "claudication_relieved_by_rest": True,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert any(r["rule_id"] == "SYMP_004_INTERMITTENT_CLAUDICATION" for r in res["triggered_rules"])

    def test_conflicting_chest_pain_self_report_resolved_conservatively(self):
        # Patient reported 'no chest pain', but described crushing pressure
        symptoms = {
            "chest_pain": False,
            "chest_pressure": True,
            "chest_pain_quality": "crushing tightness",
            "substernal_location": True,
            "exertional_provocation": True,
            "relieved_by_rest": True,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert len(res["detected_conflicts"]) > 0
        conflict = res["detected_conflicts"][0]
        assert conflict["conflict_id"] == "CONFLICT_CHEST_PAIN_SELF_REPORT"
        # Must resolve to Typical Angina despite initial False checkbox
        assert res["angina_classification"] == "typical_angina"

    def test_conflicting_dyspnea_vs_objective_hypoxia(self):
        # Patient reports no dyspnea, but pulse oximetry shows 87% SpO2
        symptoms = {"dyspnea": False}
        vitals = {"spo2": 87.0}
        res = evaluate_symptom_rules(patient_symptoms=symptoms, measured_vitals=vitals)
        assert len(res["detected_conflicts"]) > 0
        conflict = next(c for c in res["detected_conflicts"] if c["conflict_id"] == "CONFLICT_DYSPNEA_VS_SPO2")
        assert "hypoxic" in conflict["description"]

    def test_incomplete_inputs_clean_tracking(self):
        # Minimal input
        symptoms = {"palpitations": True}
        res = evaluate_symptom_rules(patient_symptoms=symptoms)
        assert "chest_pain" in res["unassessed_features"]
        assert "dyspnea" in res["unassessed_features"]
        assert res["angina_classification"] == "none"


    def test_ordinary_non_urgent_presentation(self):
        # Routine checkup, no cardiac symptoms
        symptoms = {
            "chest_pain": False,
            "dyspnea": False,
            "palpitations": False,
            "syncope": False,
        }
        vitals = {
            "systolic_bp": 122.0,
            "diastolic_bp": 78.0,
            "heart_rate": 72.0,
            "spo2": 98.0,
        }
        res = evaluate_symptom_rules(patient_symptoms=symptoms, measured_vitals=vitals)
        assert res["triggered_count"] == 0
        assert res["angina_classification"] == "none"
        assert res["congestive_symptom_score"] == 0


class TestDiagnosticTestRecommendations:
    """Test suite for evidence-based secondary testing suggestions."""

    def test_chest_pain_recommends_ecg_and_troponin(self):
        symptoms = {"chest_pain": True}
        res = generate_test_recommendations(patient_symptoms=symptoms)
        test_names = res["recommended_test_names"]
        assert any("ECG" in t for t in test_names)
        assert any("Troponin" in t for t in test_names)

        # Check evidence class
        ecg_rec = next(r for r in res["recommendations"] if "ECG" in r["title"])
        assert ecg_rec["metadata"]["recommendation_class"] == "Class I"

    def test_congestive_dyspnea_recommends_bnp_and_echo(self):
        symptoms = {
            "dyspnea": True,
            "bilateral_leg_edema": True,
            "orthopnea": True,
        }
        symptom_eval = {"congestive_symptom_score": 3, "angina_classification": "none"}
        res = generate_test_recommendations(patient_symptoms=symptoms, symptom_eval=symptom_eval)
        test_names = res["recommended_test_names"]
        assert any("Natriuretic" in t or "BNP" in t for t in test_names)
        assert any("Echocardiogram" in t or "TTE" in t for t in test_names)

    def test_palpitations_recommends_ambulatory_holter(self):
        symptoms = {"palpitations": True}
        res = generate_test_recommendations(patient_symptoms=symptoms)
        test_names = res["recommended_test_names"]
        assert any("Ambulatory ECG" in t or "Holter" in t for t in test_names)

    def test_stable_angina_recommends_ccta_or_stress(self):
        symptoms = {"chest_pain": True, "substernal_location": True}
        symptom_eval = {"angina_classification": "atypical_angina", "congestive_symptom_score": 0}
        res = generate_test_recommendations(patient_symptoms=symptoms, symptom_eval=symptom_eval)
        test_names = res["recommended_test_names"]
        assert any("CCTA" in t or "Stress" in t for t in test_names)

    def test_primary_prevention_risk_factors_recommend_lab_panel(self):
        history = {"hypertension": True, "smoking": True, "age": 55}
        res = generate_test_recommendations(clinical_history=history)
        test_names = res["recommended_test_names"]
        assert any("Metabolic" in t or "Lipid" in t for t in test_names)


class TestUnifiedClinicalSafetyCoordinator:
    """Test suite for evaluate_clinical_safety coordinating all engines."""

    def test_unified_coordinator_emergency_primacy(self):
        symptoms = {
            "chest_pain": True,
            "chest_pain_quality": "crushing heaviness",
            "chest_pain_radiation": "left arm and jaw",
            "diaphoresis": True,
        }
        vitals = {"systolic_bp": 145.0, "heart_rate": 88.0, "spo2": 96.0}
        ml_context = {"score": 0.05}  # Low ML score

        res = evaluate_clinical_safety(
            patient_symptoms=symptoms,
            measured_vitals=vitals,
            ml_context=ml_context,
        )

        assert res["status"] == "success"
        assert res["is_emergency"] is True
        assert res["overall_urgency"] == RulePriority.EMERGENCY_IMMEDIATE.value
        assert "EMERGENCY PRIMACY" in res["clinical_safety_notice"]
        assert res["emergency_triage"]["is_emergency"] is True
        assert len(res["diagnostic_recommendations"]["recommendations"]) > 0

    def test_unified_coordinator_non_urgent(self):
        symptoms = {"chest_pain": False, "dyspnea": False}
        vitals = {"systolic_bp": 120.0, "diastolic_bp": 80.0, "heart_rate": 70.0, "spo2": 99.0}
        res = evaluate_clinical_safety(patient_symptoms=symptoms, measured_vitals=vitals)

        assert res["status"] == "success"
        assert res["is_emergency"] is False
        assert res["overall_urgency"] == RulePriority.ROUTINE_OUTPATIENT.value
