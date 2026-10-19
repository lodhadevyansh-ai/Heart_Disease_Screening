"""
Machine Learning Inference and Prediction Persistence Service.

CRITICAL CLINICAL & ARCHITECTURAL MANDATES:
1. Calls Machine_Learning/src/predict.py directly.
2. Explicitly maps API and clinical entity fields to model inputs. Never passes unvalidated fields blindly.
3. NEVER silently imputes missing clinical parameters to force a prediction.
4. Returns explicit unsupported statuses for invalid tasks (e.g. heart failure screening on unselected patients).
5. Persists prediction history preserving the exact model version, target definition, and feature snapshots.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.extensions import db
from backend.schemas.prediction_schema import PredictionRequestSchema
from database.models import Assessment, ModelPrediction, StructuredLabMeasurement
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
                "task_id": task_key,
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

    @classmethod
    def persist_direct_clinical_features(
        cls,
        assessment_id: int,
        task_name: str,
        direct_features: Dict[str, Any],
    ) -> None:
        """
        Persist validated clinical parameters supplied during inference directly
        into StructuredLabMeasurement rows linked to the encounter, ensuring provenance,
        traceability, and persistence upon page reload.
        """
        canonical_task = resolve_canonical_task(task_name)
        now_utc = datetime.now(timezone.utc)

        # Specifications for clinical tests corresponding to model features
        CAD_SPECS = {
            "thalach": ("maximum_heart_rate", "bpm", "numeric"),
            "thalch": ("maximum_heart_rate", "bpm", "numeric"),
            "chol": ("cholesterol", "mg/dL", "numeric"),
            "fbs": ("fasting_blood_sugar", "boolean_flag", "binary"),
            "restecg": ("restecg", "category", "text"),
            "oldpeak": ("oldpeak", "mm", "numeric"),
            "slope": ("slope", "category", "text"),
            "ca": ("ca", "major_vessels_count", "numeric"),
            "thal": ("thal", "category", "text"),
        }

        HF_SPECS = {
            "creatinine_phosphokinase": ("creatinine_phosphokinase", "U/L", "numeric"),
            "ejection_fraction": ("ejection_fraction", "%", "numeric"),
            "platelets": ("platelets", "/mcL", "numeric"),
            "serum_creatinine": ("serum_creatinine", "mg/dL", "numeric"),
            "serum_sodium": ("serum_sodium", "mEq/L", "numeric"),
            "anaemia": ("anaemia", "boolean_flag", "binary"),
            "diabetes": ("diabetes", "boolean_flag", "binary"),
            "smoking": ("smoking", "boolean_flag", "binary"),
        }

        specs = (
            CAD_SPECS if canonical_task == "coronary_artery_disease"
            else HF_SPECS if canonical_task == "heart_failure_mortality"
            else {}
        )

        for feat_key, (test_name, unit, val_type) in specs.items():
            if feat_key in direct_features and direct_features[feat_key] not in (None, ""):
                raw_val = direct_features[feat_key]
                val_num = None
                val_txt = None

                try:
                    if val_type == "numeric":
                        val_num = float(raw_val)
                        val_txt = str(raw_val)
                    elif val_type == "binary":
                        is_pos = raw_val in (1, True, "1", "true", "True")
                        val_num = 1.0 if is_pos else 0.0
                        val_txt = "1" if is_pos else "0"
                    else:
                        val_txt = str(raw_val).strip()
                except (ValueError, TypeError):
                    continue

                existing = (
                    StructuredLabMeasurement.query.filter_by(
                        assessment_id=assessment_id,
                        test_name=test_name,
                    ).first()
                )
                if existing:
                    existing.value_numeric = val_num
                    existing.value_text = val_txt
                    existing.unit = unit
                    existing.recorded_at = now_utc
                else:
                    meas = StructuredLabMeasurement(
                        assessment_id=assessment_id,
                        test_name=test_name,
                        value_numeric=val_num,
                        value_text=val_txt,
                        unit=unit,
                        flag="normal",
                        recorded_at=now_utc,
                    )
                    db.session.add(meas)

        # Also persist vitals and symptoms if provided in direct_features and not already recorded
        from database.models import VitalSign, PatientSymptom
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if assessment:
            if "trestbps" in direct_features and direct_features["trestbps"] not in (None, ""):
                try:
                    bp_val = float(direct_features["trestbps"])
                    if assessment.vitals:
                        if assessment.vitals.systolic_bp is None:
                            assessment.vitals.systolic_bp = bp_val
                    else:
                        assessment.vitals = VitalSign(assessment_id=assessment_id, systolic_bp=bp_val)
                except (ValueError, TypeError):
                    pass

            if "cp" in direct_features and direct_features["cp"] not in (None, ""):
                cp_str = str(direct_features["cp"]).lower().strip()
                inv_map = {
                    "typical angina": "typical_angina",
                    "atypical angina": "atypical_angina",
                    "non-anginal": "non_anginal",
                    "asymptomatic": "none",
                }
                c_class = inv_map.get(cp_str, "none")
                if assessment.symptoms:
                    if assessment.symptoms.angina_classification is None:
                        assessment.symptoms.angina_classification = c_class
                else:
                    assessment.symptoms = PatientSymptom(assessment_id=assessment_id, angina_classification=c_class)

            if "exang" in direct_features and direct_features["exang"] not in (None, ""):
                is_exang = direct_features["exang"] in (1, True, "1", "true", "True")
                if assessment.symptoms:
                    if assessment.symptoms.exertional_provocation is None:
                        assessment.symptoms.exertional_provocation = is_exang
                else:
                    assessment.symptoms = PatientSymptom(assessment_id=assessment_id, exertional_provocation=is_exang)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def map_assessment_to_features(
        assessment: Assessment,
        task_name: str,
        direct_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Map clinical assessment entities explicitly to model input features.
        Preserves legitimate clinical zeros (e.g. oldpeak=0.0, ca=0, exang=0).
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

            # Direct feature aliases
            if "thalach" in direct and "thalch" not in direct:
                direct["thalch"] = direct["thalach"]
            elif "thalch" in direct and "thalach" not in direct:
                direct["thalach"] = direct["thalch"]

            # Start with explicit direct feature overrides if provided
            for k in required_keys:
                if k in direct and direct[k] not in (None, ""):
                    val = direct[k]
                    if k in ("trestbps", "chol", "thalch", "oldpeak"):
                        try:
                            mapped[k] = float(val)
                        except (ValueError, TypeError):
                            mapped[k] = val
                    elif k in ("age", "ca"):
                        try:
                            mapped[k] = int(val)
                        except (ValueError, TypeError):
                            mapped[k] = val
                    elif k in ("fbs", "exang"):
                        if val in (1, True, "1", "true", "True"):
                            mapped[k] = 1
                        elif val in (0, False, "0", "false", "False"):
                            mapped[k] = 0
                        else:
                            mapped[k] = val
                    elif k in ("restecg", "slope", "thal"):
                        mapped[k] = str(val).strip().lower()
                    elif k in ("sex", "cp"):
                        mapped[k] = str(val).strip()
                    else:
                        mapped[k] = val

            # Demographics (Selected patient is authoritative source)
            if "age" not in mapped and assessment.patient:
                pt_age = getattr(assessment.patient, "age", None)
                if pt_age is None:
                    pt_age = getattr(assessment.patient, "patient_age", None)
                if pt_age is not None:
                    try:
                        mapped["age"] = int(pt_age)
                    except (ValueError, TypeError):
                        mapped["age"] = pt_age
                elif hasattr(assessment.patient, "date_of_birth") or hasattr(assessment.patient, "dob"):
                    dob = getattr(assessment.patient, "date_of_birth", None) or getattr(assessment.patient, "dob", None)
                    if dob:
                        ref_date = assessment.assessment_date or datetime.now(timezone.utc)
                        try:
                            if isinstance(dob, str):
                                dob = datetime.fromisoformat(dob.replace("Z", "+00:00"))
                            mapped["age"] = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
                        except Exception:
                            pass

            if "sex" not in mapped and assessment.patient:
                raw_sex = getattr(assessment.patient, "sex", None) or getattr(assessment.patient, "biological_sex", None) or getattr(assessment.patient, "gender", None)
                if raw_sex:
                    clean_s = str(raw_sex).strip().capitalize()
                    mapped["sex"] = "Male" if clean_s in ("Male", "M", "1") else ("Female" if clean_s in ("Female", "F", "0") else clean_s)

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

            # NOTE: Resting heart rate (vitals.heart_rate) is clinically distinct from
            # maximum exercise heart rate (thalach/thalch) and MUST NEVER be substituted.

            # Structured lab measurements
            lab_dict: Dict[str, Any] = {}
            for lab in assessment.lab_measurements:
                lab_dict[lab.test_name.lower()] = lab.value_numeric if lab.value_numeric is not None else lab.value_text

            if "chol" not in mapped:
                for k in ("cholesterol", "chol", "total_cholesterol"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        try:
                            mapped["chol"] = float(lab_dict[k])
                            break
                        except (ValueError, TypeError):
                            pass

            if "fbs" not in mapped:
                for k in ("fasting_blood_sugar", "fbs", "glucose"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        try:
                            num_val = float(lab_dict[k])
                            if num_val in (0.0, 1.0) and k in ("fasting_blood_sugar", "fbs"):
                                mapped["fbs"] = int(num_val)
                            else:
                                mapped["fbs"] = 1 if num_val > 120.0 else 0
                            break
                        except (ValueError, TypeError):
                            pass

            if "restecg" not in mapped:
                for k in ("restecg", "rest_ecg", "ecg"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        mapped["restecg"] = str(lab_dict[k]).lower().strip()
                        break

            if "oldpeak" not in mapped:
                for k in ("oldpeak", "st_depression"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        try:
                            mapped["oldpeak"] = float(lab_dict[k])
                            break
                        except (ValueError, TypeError):
                            pass

            if "slope" not in mapped:
                for k in ("slope", "st_slope"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        mapped["slope"] = str(lab_dict[k]).lower().strip()
                        break

            if "ca" not in mapped:
                for k in ("ca", "major_vessels", "fluoroscopy_vessels"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        try:
                            mapped["ca"] = int(float(lab_dict[k]))
                            break
                        except (ValueError, TypeError):
                            pass

            if "thal" not in mapped:
                for k in ("thal", "thalassemia"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        mapped["thal"] = str(lab_dict[k]).lower().strip()
                        break

            # Structured lab measurement for maximum exercise heart rate (thalach/thalch)
            if "thalch" not in mapped and "thalach" not in mapped:
                for k in ("maximum_heart_rate", "thalach", "thalch", "max_heart_rate", "max_hr"):
                    if k in lab_dict and lab_dict[k] not in (None, ""):
                        try:
                            val_hr = float(lab_dict[k])
                            mapped["thalch"] = val_hr
                            mapped["thalach"] = val_hr
                            break
                        except (ValueError, TypeError):
                            pass
            elif "thalch" in mapped and "thalach" not in mapped:
                mapped["thalach"] = mapped["thalch"]
            elif "thalach" in mapped and "thalch" not in mapped:
                mapped["thalch"] = mapped["thalach"]

            return mapped

        # ---------------------------------------------------------------------
        # Task 2: Heart Failure Mortality Risk
        # ---------------------------------------------------------------------
        elif canonical_task == "heart_failure_mortality":
            required_keys = SUPPORTED_TASKS["heart_failure_mortality"]["required_features"]
            mapped: Dict[str, Any] = {}

            for k in required_keys:
                if k in direct and direct[k] not in (None, ""):
                    val = direct[k]
                    if k in ("creatinine_phosphokinase", "ejection_fraction", "platelets", "serum_creatinine", "serum_sodium"):
                        try:
                            mapped[k] = float(val)
                        except (ValueError, TypeError):
                            mapped[k] = val
                    elif k == "age":
                        try:
                            mapped[k] = int(val)
                        except (ValueError, TypeError):
                            mapped[k] = val
                    elif k in ("anaemia", "diabetes", "high_blood_pressure", "smoking"):
                        if val in (1, True, "1", "true", "True"):
                            mapped[k] = 1
                        elif val in (0, False, "0", "false", "False"):
                            mapped[k] = 0
                        else:
                            mapped[k] = val
                    elif k == "sex":
                        mapped[k] = 1 if str(val).strip().lower() in ("1", "male") else 0
                    else:
                        mapped[k] = val

            if "age" not in mapped and assessment.patient:
                pt_age = getattr(assessment.patient, "age", None) or getattr(assessment.patient, "patient_age", None)
                if pt_age is not None:
                    try:
                        mapped["age"] = int(pt_age)
                    except (ValueError, TypeError):
                        mapped["age"] = pt_age
            if "sex" not in mapped and assessment.patient:
                raw_sex = getattr(assessment.patient, "sex", None) or getattr(assessment.patient, "biological_sex", None) or getattr(assessment.patient, "gender", None)
                if raw_sex:
                    clean_s = str(raw_sex).strip().lower()
                    mapped["sex"] = 1 if clean_s in ("male", "m", "1") else 0

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
                ("creatinine_phosphokinase", ["creatinine_phosphokinase", "cpk", "ck"]),
                ("anaemia", ["anaemia", "anemia"]),
                ("diabetes", ["diabetes"]),
                ("smoking", ["smoking", "tobacco", "smoker"]),
            ]:
                if key not in mapped:
                    for ln in lab_names:
                        if ln in lab_dict and lab_dict[ln] not in (None, ""):
                            try:
                                mapped[key] = float(lab_dict[ln])
                                break
                            except (ValueError, TypeError):
                                pass

            # Clinical lab derivation: Anaemia from Hemoglobin (< 12 g/dL)
            if "anaemia" not in mapped:
                for ln in ["hemoglobin", "hb", "hgb"]:
                    if ln in lab_dict and lab_dict[ln] not in (None, ""):
                        try:
                            mapped["anaemia"] = 1 if float(lab_dict[ln]) < 12.0 else 0
                            break
                        except (ValueError, TypeError):
                            pass

            # Clinical lab derivation: Diabetes from Fasting Glucose (>= 126 mg/dL) or HbA1c (>= 6.5%)
            if "diabetes" not in mapped:
                for ln in ["fasting_glucose", "fbs", "glucose"]:
                    if ln in lab_dict and lab_dict[ln] not in (None, ""):
                        try:
                            mapped["diabetes"] = 1 if float(lab_dict[ln]) >= 126.0 else 0
                            break
                        except (ValueError, TypeError):
                            pass
                if "diabetes" not in mapped and "hba1c" in lab_dict and lab_dict["hba1c"] not in (None, ""):
                    try:
                        mapped["diabetes"] = 1 if float(lab_dict["hba1c"]) >= 6.5 else 0
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
        persist input parameters as StructuredLabMeasurement, and save prediction
        record with full target definitions and model metadata.

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

        task_name = (data.task_name or data.task or "").strip()
        if not task_name:
            return False, None, "Task name must be specified.", 400

        # Check explicit unsupported tasks first
        if task_name.lower() in UNSUPPORTED_TASKS:
            return (
                False,
                None,
                UNSUPPORTED_TASKS[task_name.lower()],
                400,
            )

        # Persist direct clinical measurements to database for encounter provenance
        if data.direct_features:
            cls.persist_direct_clinical_features(
                assessment_id=assessment_id,
                task_name=task_name,
                direct_features=data.direct_features,
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

        # Check for identical duplicate prediction on retry
        canonical = resolve_canonical_task(task_name)
        existing_pred = (
            ModelPrediction.query.filter_by(
                assessment_id=assessment_id,
                task_name=canonical,
            )
            .order_by(ModelPrediction.created_at.desc())
            .first()
        )
        if existing_pred and existing_pred.input_features_snapshot == mapped_features:
            return True, existing_pred, None, 200

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

    @classmethod
    def check_task_readiness(cls, assessment_id: int) -> Dict[str, Any]:
        """
        Evaluate which supported ML tasks can run on this assessment encounter's
        available clinical data (demographics, symptoms, vitals, structured labs).
        Preserves legitimate zeros (0, 0.0) as valid features.
        """
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        if not assessment:
            return {}

        readiness: Dict[str, Any] = {}
        for task_key, cfg in SUPPORTED_TASKS.items():
            if task_key == "arrhythmia_ecg":
                readiness[task_key] = {
                    "task_name": task_key,
                    "task_id": task_key,
                    "ready": False,
                    "missing_features": ["279 precomputed ECG wave metrics"],
                    "available_features_count": 0,
                    "required_features_count": 279,
                    "score_type": cfg["score_type"],
                    "is_probability_calibrated": cfg["is_probability_calibrated"],
                }
                continue

            try:
                mapped = cls.map_assessment_to_features(assessment=assessment, task_name=task_key)
            except Exception:
                mapped = {}

            required = cfg.get("required_features", [])
            # Legitimate zeros (0, 0.0) are valid; only None or empty string are missing
            missing = [f for f in required if f not in mapped or mapped[f] in (None, "")]

            readiness[task_key] = {
                "task_name": task_key,
                "task_id": task_key,
                "ready": len(missing) == 0,
                "missing_features": missing,
                "available_features": mapped,
                "available_features_count": len([f for f in required if f in mapped and mapped[f] not in (None, "")]),
                "required_features_count": len(required),
                "score_type": cfg["score_type"],
                "is_probability_calibrated": cfg["is_probability_calibrated"],
            }

        return readiness
