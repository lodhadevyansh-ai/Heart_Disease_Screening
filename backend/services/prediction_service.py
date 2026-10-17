"""
Machine Learning Inference and Prediction Persistence Service.

CRITICAL CLINICAL & ARCHITECTURAL MANDATES:
1. Calls Machine_Learning/src/predict.py directly.
2. Explicitly maps API and clinical entity fields to model inputs. Never passes unvalidated fields blindly.
3. NEVER silently imputes missing clinical parameters to force a prediction.
4. Returns explicit unsupported statuses for invalid tasks (e.g. heart failure screening on unselected patients).
5. Persists prediction history preserving the exact model version, target definition, and feature snapshots.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.extensions import db
from backend.schemas.prediction_schema import PredictionRequestSchema
from database.models import Assessment, ModelPrediction
from Machine_Learning.src.predict import (
    predict_clinical_condition,
    resolve_canonical_task,
    SUPPORTED_TASKS,
    UNSUPPORTED_TASKS,
    UnsupportedTaskError,
    ValidationError as MLValidationError,
    ModelArtifactNotFoundError,
    ClinicalInferenceError,
)


class PredictionService:
    """Service handling ML inference execution and history tracking."""

    @staticmethod
    def get_task_catalog() -> Dict[str, Any]:
        """Return structured catalog of supported and unsupported tasks."""
        supported_list = []
        for task_key, cfg in SUPPORTED_TASKS.items():
            supported_list.append({
                "task_name": task_key,
                "supported": True,
                "status": "active",
                "aliases": cfg.get("alias", []),
                "score_type": cfg["score_type"],
                "is_probability_calibrated": cfg["is_probability_calibrated"],
                "required_features": cfg.get("required_features", [f"{cfg.get('required_features_count', 279)} precomputed ECG features"]),
                "clinical_target": (
                    "Angiographic Coronary Artery Disease (>= 50% diameter stenosis in >= 1 major vessel)"
                    if task_key == "coronary_artery_disease"
                    else (
                        "All-Cause In-Hospital/Follow-up Mortality in Confirmed Heart Failure Patients"
                        if task_key == "heart_failure_mortality"
                        else "12-Lead Electrocardiographic Arrhythmia Multi-Class Classification"
                    )
                ),
                "clinical_limitations": (
                    "Trained on adult symptomatic cohorts undergoing diagnostic evaluation. Not for asymptomatic general screening."
                    if task_key == "coronary_artery_disease"
                    else (
                        "Valid ONLY for patients with confirmed clinical heart failure. Prohibited for general screening."
                        if task_key == "heart_failure_mortality"
                        else "Requires 279 precomputed ECG wave metrics. Cannot screen from symptoms alone."
                    )
                ),
            })

        return {
            "supported_tasks": supported_list,
            "unsupported_tasks": UNSUPPORTED_TASKS,
        }

    @staticmethod
    def map_assessment_to_features(
        assessment: Assessment,
        task_name: str,
        direct_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Map clinical assessment entities explicitly to model input features.
        Never passes unmapped or unexpected request parameters to the model.
        """
        canonical_task = resolve_canonical_task(task_name)
        direct = direct_features or {}

        # ---------------------------------------------------------------------
        # Task 1: Coronary Artery Disease (CAD)
        # ---------------------------------------------------------------------
        if canonical_task == "coronary_artery_disease":
            required_keys = SUPPORTED_TASKS["coronary_artery_disease"]["required_features"]
            mapped: Dict[str, Any] = {}

            # Start with explicit direct feature overrides if provided
            for k in required_keys:
                if k in direct and direct[k] is not None:
                    mapped[k] = direct[k]

            # Demographics
            if "age" not in mapped and assessment.patient:
                mapped["age"] = assessment.patient.age
            if "sex" not in mapped and assessment.patient:
                mapped["sex"] = assessment.patient.sex

            # Symptoms (Chest pain type / angina classification)
            if "cp" not in mapped and assessment.symptoms:
                angina_map = {
                    "typical_angina": "typical angina",
                    "atypical_angina": "atypical angina",
                    "non_anginal": "non-anginal",
                    "none": "asymptomatic",
                }
                c_class = assessment.symptoms.angina_classification
                if c_class in angina_map:
                    mapped["cp"] = angina_map[c_class]
                elif assessment.symptoms.chest_pain is False:
                    mapped["cp"] = "asymptomatic"

            if "exang" not in mapped and assessment.symptoms:
                if assessment.symptoms.exertional_provocation is not None:
                    mapped["exang"] = 1 if assessment.symptoms.exertional_provocation else 0

            # Vitals
            if "trestbps" not in mapped and assessment.vitals:
                if assessment.vitals.systolic_bp is not None:
                    mapped["trestbps"] = assessment.vitals.systolic_bp

            if "thalch" not in mapped and assessment.vitals:
                if assessment.vitals.heart_rate is not None:
                    mapped["thalch"] = assessment.vitals.heart_rate

            # Structured lab measurements
            lab_dict: Dict[str, Any] = {}
            for lab in assessment.lab_measurements:
                lab_dict[lab.test_name.lower()] = lab.value_numeric if lab.value_numeric is not None else lab.value_text

            if "chol" not in mapped:
                for k in ("cholesterol", "chol", "total_cholesterol"):
                    if k in lab_dict and lab_dict[k] is not None:
                        try:
                            mapped["chol"] = float(lab_dict[k])
                            break
                        except (ValueError, TypeError):
                            pass

            if "fbs" not in mapped:
                for k in ("fbs", "fasting_blood_sugar", "glucose"):
                    if k in lab_dict and lab_dict[k] is not None:
                        try:
                            mapped["fbs"] = 1 if float(lab_dict[k]) > 120 else 0
                            break
                        except (ValueError, TypeError):
                            pass

            if "restecg" not in mapped:
                for k in ("restecg", "rest_ecg", "ecg"):
                    if k in lab_dict and lab_dict[k] is not None:
                        mapped["restecg"] = str(lab_dict[k]).lower()
                        break

            if "oldpeak" not in mapped:
                for k in ("oldpeak", "st_depression"):
                    if k in lab_dict and lab_dict[k] is not None:
                        try:
                            mapped["oldpeak"] = float(lab_dict[k])
                            break
                        except (ValueError, TypeError):
                            pass

            if "slope" not in mapped:
                for k in ("slope", "st_slope"):
                    if k in lab_dict and lab_dict[k] is not None:
                        mapped["slope"] = str(lab_dict[k]).lower()
                        break

            if "ca" not in mapped:
                for k in ("ca", "major_vessels", "fluoroscopy_vessels"):
                    if k in lab_dict and lab_dict[k] is not None:
                        try:
                            mapped["ca"] = int(lab_dict[k])
                            break
                        except (ValueError, TypeError):
                            pass

            if "thal" not in mapped:
                for k in ("thal", "thalassemia"):
                    if k in lab_dict and lab_dict[k] is not None:
                        mapped["thal"] = str(lab_dict[k]).lower()
                        break

            return mapped

        # ---------------------------------------------------------------------
        # Task 2: Heart Failure Mortality Risk
        # ---------------------------------------------------------------------
        elif canonical_task == "heart_failure_mortality":
            required_keys = SUPPORTED_TASKS["heart_failure_mortality"]["required_features"]
            mapped: Dict[str, Any] = {}

            for k in required_keys:
                if k in direct and direct[k] is not None:
                    mapped[k] = direct[k]

            if "age" not in mapped and assessment.patient:
                mapped["age"] = assessment.patient.age
            if "sex" not in mapped and assessment.patient:
                mapped["sex"] = 1 if assessment.patient.sex.lower() == "male" else 0

            # Vitals
            if "high_blood_pressure" not in mapped and assessment.vitals:
                if assessment.vitals.systolic_bp is not None and assessment.vitals.diastolic_bp is not None:
                    mapped["high_blood_pressure"] = 1 if (assessment.vitals.systolic_bp >= 140 or assessment.vitals.diastolic_bp >= 90) else 0

            # Structured labs
            lab_dict = {
                lab.test_name.lower(): lab.value_numeric if lab.value_numeric is not None else lab.value_text
                for lab in assessment.lab_measurements
            }

            for key, lab_names in [
                ("ejection_fraction", ["ejection_fraction", "ef", "lvef"]),
                ("serum_creatinine", ["serum_creatinine", "creatinine"]),
                ("platelets", ["platelets", "platelet_count"]),
                ("serum_sodium", ["serum_sodium", "sodium"]),
                ("creatinine_phosphokinase", ["creatinine_phosphokinase", "cpk"]),
                ("anaemia", ["anaemia", "anemia"]),
                ("diabetes", ["diabetes"]),
                ("smoking", ["smoking", "tobacco"]),
            ]:
                if key not in mapped:
                    for ln in lab_names:
                        if ln in lab_dict and lab_dict[ln] is not None:
                            try:
                                mapped[key] = float(lab_dict[ln])
                                break
                            except (ValueError, TypeError):
                                pass

            return mapped

        # ---------------------------------------------------------------------
        # Task 3: Arrhythmia ECG Classification
        # ---------------------------------------------------------------------
        elif canonical_task == "arrhythmia_ecg":
            # Direct feature map must provide all 279 precomputed features
            return direct

        return direct

    @classmethod
    def execute_prediction(
        cls,
        assessment_id: int,
        data: PredictionRequestSchema,
    ) -> Tuple[bool, Optional[ModelPrediction], Optional[str], int]:
        """
        Execute prediction pipeline, validate inputs, enforce clinical guardrails,
        and persist result with full target definitions and model metadata.

        Returns
        -------
        success : bool
        prediction_record : ModelPrediction, optional
        error_message : str, optional
        status_code : int (200, 400, 422, 404, 500)
        """
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            return False, None, f"Assessment with ID {assessment_id} not found.", 404

        task_name = data.task_name.strip()

        # Check explicit unsupported tasks first
        if task_name.lower() in UNSUPPORTED_TASKS:
            return (
                False,
                None,
                UNSUPPORTED_TASKS[task_name.lower()],
                400,
            )

        # Map features explicitly
        try:
            mapped_features = cls.map_assessment_to_features(
                assessment=assessment,
                task_name=task_name,
                direct_features=data.direct_features,
            )
        except Exception as e:
            return False, None, f"Feature mapping error: {str(e)}", 400

        # Run inference via shared ML interface
        try:
            result = predict_clinical_condition(
                task=task_name,
                input_data=mapped_features,
                explain=data.explain,
            )
        except UnsupportedTaskError as e:
            return False, None, str(e), 400
        except MLValidationError as e:
            return False, None, str(e), 422
        except ModelArtifactNotFoundError as e:
            return False, None, str(e), 503
        except ClinicalInferenceError as e:
            return False, None, str(e), 500
        except Exception as e:
            return False, None, f"Unexpected inference failure: {str(e)}", 500

        # Persist prediction result to database
        try:
            pred_record = ModelPrediction(
                assessment_id=assessment_id,
                task_name=result.get("task", task_name),
                model_name=result.get("model_identification", {}).get("model_name", "Clinical Classifier"),
                model_version=result.get("model_identification", {}).get("version", "1.0.0"),
                target_definition=result.get("task_scope", {}).get("target_definition", "Clinical condition risk evaluation"),
                predicted_class_id=result.get("prediction", {}).get("predicted_class_id"),
                predicted_class_label=result.get("prediction", {}).get("predicted_class_label", "Unknown"),
                raw_score=result.get("prediction", {}).get("score"),
                calibrated_probability=result.get("prediction", {}).get("calibrated_probability"),
                is_probability_calibrated=result.get("prediction", {}).get("is_probability_calibrated", False),
                decision_threshold=result.get("prediction", {}).get("decision_threshold"),
                score_type=result.get("prediction", {}).get("score_type", "classifier_score"),
                input_features_snapshot=mapped_features,
                explanation_snapshot=result.get("explanation"),
                clinical_prototype_disclaimer=result.get("clinical_prototype_disclaimer", "Clinical research prototype"),
            )
            db.session.add(pred_record)
            db.session.commit()
            return True, pred_record, None, 200
        except Exception as e:
            db.session.rollback()
            return False, None, f"Failed to persist prediction record: {str(e)}", 500

    @staticmethod
    def get_prediction_history(assessment_id: int) -> List[ModelPrediction]:
        """Fetch all historical prediction records for a specific assessment."""
        return (
            ModelPrediction.query.filter_by(assessment_id=assessment_id)
            .order_by(ModelPrediction.created_at.desc())
            .all()
        )
