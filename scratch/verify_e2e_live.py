"""
Live End-to-End Workflow Verification Script (Complete Suite).
Connects directly to the running Flask server (http://127.0.0.1:5000)
and verifies Vite frontend responses (http://127.0.0.1:5173).
"""

import json
import urllib.request
import urllib.error
import sys

API_BASE = "http://127.0.0.1:5000/api/v1"
FRONTEND_BASE = "http://127.0.0.1:5173"

def make_request(url, method="GET", data=None, headers=None):
    hdrs = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_body = response.read().decode("utf-8")
            return response.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        return e.code, json.loads(resp_body) if resp_body else {}
    except Exception as e:
        return 0, {"error": str(e)}

def run_e2e_verification():
    print("=" * 70)
    print("LIVE END-TO-END WORKFLOW & SAFETY VERIFICATION")
    print(f"Backend API: {API_BASE}")
    print(f"Frontend:   {FRONTEND_BASE}")
    print("=" * 70)

    # 0. Check Frontend Dev Server
    try:
        with urllib.request.urlopen(FRONTEND_BASE, timeout=5) as fe_resp:
            print(f"[OK] Frontend HTTP Status: {fe_resp.status} (Serving CardioCare AI HTML)")
    except Exception as e:
        print(f"[FAIL] Frontend inaccessible: {e}")
        return False

    # 1. Health check on Backend
    status, health = make_request(f"{API_BASE}/health")
    print(f"[OK] Backend Health: HTTP {status} -> {health.get('data', {}).get('status')}")
    assert status == 200

    # 2. Authenticate Clinician Demo
    login_payload = {
        "username": "clinician_demo",
        "password": "ClinicianPass123!"
    }
    status, auth_res = make_request(f"{API_BASE}/auth/login", method="POST", data=login_payload)
    print(f"[OK] Step 0 - Login: HTTP {status} -> Clinician Token Issued")
    assert status == 200
    token = auth_res["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create a synthetic patient profile
    pt_payload = {
        "first_name": "Synthea",
        "last_name": "IntegrationTest",
        "medical_record_number": "MRN-E2E-LIVE-2026",
        "age": 63,
        "sex": "Male",
        "smoking_status": "former",
        "has_diabetes": False,
        "has_hypertension": True,
        "notes": "End-to-end integration test synthetic subject."
    }
    status, pt_res = make_request(f"{API_BASE}/patients", method="POST", data=pt_payload, headers=auth_headers)
    print(f"[OK] Step 1 - Create Patient Profile: HTTP {status} -> Code: {pt_res['data']['patient_code']}")
    assert status == 201
    patient_id = pt_res["data"]["id"]

    # Step 2: Create assessment encounter and record symptoms
    assess_payload = {
        "reason_for_visit": "Subacute exertional tightness and dyspnea screening"
    }
    status, assess_res = make_request(f"{API_BASE}/patients/{patient_id}/assessments", method="POST", data=assess_payload, headers=auth_headers)
    print(f"[OK] Step 2 - Create Encounter: HTTP {status} -> Encounter ID: {assess_res['data']['id']}")
    assert status == 201
    assessment_id = assess_res["data"]["id"]

    symptom_payload = {
        "chest_pain": True,
        "substernal_location": True,
        "exertional_provocation": True,
        "relieved_by_rest": True,
        "angina_classification": "typical_angina",
        "shortness_of_breath": True,
        "dyspnea_trigger": "exertion",
        "unusual_fatigue": False,
        "leg_swelling": False,
        "palpitations": False,
        "syncope": False,
        "diaphoresis": False
    }
    status, sym_res = make_request(f"{API_BASE}/assessments/{assessment_id}/symptoms", method="POST", data=symptom_payload, headers=auth_headers)
    print(f"[OK] Step 2b - Ingest Symptoms: HTTP {status} -> Angina Classification: {sym_res['data']['angina_classification']}")
    assert status == 200

    # Step 3 & 4: Evaluate Emergency Rules & Test Recommendations independently of ML
    status, rec_res = make_request(f"{API_BASE}/assessments/{assessment_id}/recommendations", headers=auth_headers)
    print(f"[OK] Step 3 & 4 - Emergency Triage & CDS Recommendations: HTTP {status}")
    rec_data = rec_res["data"]
    print(f"      - Red-Flag Emergency: {rec_data['is_emergency']} (Priority: {rec_data['overall_urgency']})")
    print(f"      - Diamond-Forrester Classification: {rec_data['symptom_evaluation']['angina_classification']}")
    num_recs = len(rec_data["diagnostic_recommendations"]["recommendations"])
    print(f"      - Guideline-Directed Secondary Recommendations: {num_recs} test pathways")
    assert status == 200
    assert rec_data["is_emergency"] is False

    # Step 5: Enter physiological vitals and structured lab measurements
    vitals_payload = {
        "systolic_bp": 142.0,
        "diastolic_bp": 88.0,
        "heart_rate": 74,
        "height_cm": 178.0,
        "weight_kg": 83.0
    }
    status, vit_res = make_request(f"{API_BASE}/assessments/{assessment_id}/vitals", method="POST", data=vitals_payload, headers=auth_headers)
    print(f"[OK] Step 5a - Record Vital Signs: HTTP {status} -> BP: {vit_res['data']['systolic_bp']}/{vit_res['data']['diastolic_bp']} mmHg, BMI: {vit_res['data']['bmi']}")
    assert status == 200

    cad_labs = [
        {"test_name": "cholesterol", "value_numeric": 242.0, "unit": "mg/dL", "reference_high": 200.0, "flag": "high"},
        {"test_name": "fbs", "value_numeric": 96.0, "unit": "mg/dL"},
        {"test_name": "restecg", "value_text": "normal"},
        {"test_name": "oldpeak", "value_numeric": 1.6},
        {"test_name": "slope", "value_text": "flat"},
        {"test_name": "ca", "value_numeric": 1},
        {"test_name": "thal", "value_text": "reversable defect"}
    ]
    for lab in cad_labs:
        status, lab_res = make_request(f"{API_BASE}/assessments/{assessment_id}/labs", method="POST", data=lab, headers=auth_headers)
        assert status == 201
    print(f"[OK] Step 5b - Record Structured Labs: {len(cad_labs)} parameters ingested into Encounter #{assessment_id}")

    # Step 6 & 7: Check Supported Model Task Catalog
    status, cat_res = make_request(f"{API_BASE}/predictions/tasks", headers=auth_headers)
    print(f"[OK] Step 6 & 7 - ML Task Catalog: HTTP {status}")
    supported_tasks = [t["task_name"] for t in cat_res["data"]["supported_tasks"]]
    print(f"      - Active Supported Tasks: {supported_tasks}")
    assert "coronary_artery_disease" in supported_tasks

    # Step 8, 9, 10: Run Calibrated CAD Model Inference and Persist Audit Snapshot
    pred_payload = {
        "task_name": "coronary_artery_disease",
        "explain": True
    }
    status, pred_res = make_request(f"{API_BASE}/assessments/{assessment_id}/predictions", method="POST", data=pred_payload, headers=auth_headers)
    print(f"[OK] Step 8, 9, 10 - Run Validated Model Inference: HTTP {status}")
    pred = pred_res["data"]
    print(f"      - Model: {pred['model_name']} v{pred['model_version']}")
    print(f"      - Target Definition: {pred['target_definition']}")
    print(f"      - Predicted Class: {pred['predicted_class_label']} (ID: {pred['predicted_class_id']})")
    print(f"      - Calibrated Probability: {pred['calibrated_probability'] * 100:.2f}% (Is Calibrated: {pred['is_probability_calibrated']})")
    print(f"      - Decision Threshold: {pred['decision_threshold']}")
    has_shap = "non_causal_disclaimer" in pred.get("explanation_snapshot", {})
    print(f"      - Feature Attribution Snapshot: Generated with non-causal disclaimer: {has_shap}")
    assert status == 200
    assert pred["is_probability_calibrated"] is True
    assert has_shap is True

    # Step 11: Retrieve and verify full history
    status, hist_res = make_request(f"{API_BASE}/assessments/{assessment_id}/predictions", headers=auth_headers)
    print(f"[OK] Step 11 - Query Prediction Audit Trail: HTTP {status} -> {len(hist_res['data'])} prediction records found")
    assert status == 200
    assert len(hist_res["data"]) >= 1

    status, enc_res = make_request(f"{API_BASE}/patients/{patient_id}/assessments", headers=auth_headers)
    print(f"[OK] Step 11b - Query Patient Encounters: HTTP {status} -> {len(enc_res['data'])} encounters found")
    assert status == 200
    assert len(enc_res["data"]) >= 1

    # --- NEGATIVE / UNSUCCESSFUL WORKFLOW VALIDATIONS ---
    print("\n--- SAFETY & RESILIENCE VALIDATIONS ---")

    # Safety Test A: Missing features rejected without silent imputation
    # Create empty assessment
    status, inc_assess = make_request(f"{API_BASE}/patients/{patient_id}/assessments", method="POST", data={}, headers=auth_headers)
    inc_id = inc_assess["data"]["id"]
    status, inc_pred = make_request(f"{API_BASE}/assessments/{inc_id}/predictions", method="POST", data={"task_name": "coronary_artery_disease"}, headers=auth_headers)
    print(f"[OK] Safety A - Missing Features Rejected: HTTP {status} (Expected 422 Unprocessable Entity)")
    assert status == 422
    assert "missing" in inc_pred["error"]["message"].lower()

    # Safety Test B: Unsupported task explicitly rejected
    status, unsup_pred = make_request(f"{API_BASE}/assessments/{assessment_id}/predictions", method="POST", data={"task_name": "heart_failure_screening"}, headers=auth_headers)
    print(f"[OK] Safety B - Unsupported Task Rejected: HTTP {status} (Expected 400 Bad Request)")
    assert status == 400
    assert "unsupported" in unsup_pred["error"]["message"].lower()

    # Safety Test C: Emergency symptom escalation primacy
    emerg_syms = {
        "chest_pain": True,
        "chest_pain_quality": "crushing pressure",
        "chest_pain_radiation": "left arm and jaw",
        "syncope": True,
        "diaphoresis": True
    }
    make_request(f"{API_BASE}/assessments/{inc_id}/symptoms", method="POST", data=emerg_syms, headers=auth_headers)
    status, emerg_recs = make_request(f"{API_BASE}/assessments/{inc_id}/recommendations", headers=auth_headers)
    print(f"[OK] Safety C - Emergency Primacy Escalation: HTTP {status}")
    print(f"      - Emergency Triggered: {emerg_recs['data']['is_emergency']}")
    print(f"      - Priority: {emerg_recs['data']['overall_urgency']}")
    assert emerg_recs["data"]["is_emergency"] is True
    assert emerg_recs["data"]["overall_urgency"] == "EMERGENCY_IMMEDIATE_911"

    # Safety Test D: Cross-patient authorization isolation
    # Authenticate as patient_demo (linked to patient ID 1)
    status, p_auth = make_request(f"{API_BASE}/auth/login", method="POST", data={"username": "patient_demo", "password": "PatientPass123!"})
    p_headers = {"Authorization": f"Bearer {p_auth['data']['access_token']}"}
    status, forbidden_res = make_request(f"{API_BASE}/patients/{patient_id}", headers=p_headers)
    print(f"[OK] Safety D - Patient Access Control: HTTP {status} (Expected 403 Forbidden for cross-patient access)")
    assert status == 403

    print("=" * 70)
    print("ALL INTEGRATION SCENARIOS (HAPPY PATH + 4 SAFETY TESTS) PASSED!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
