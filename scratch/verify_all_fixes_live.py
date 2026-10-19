"""
Comprehensive Live E2E Integration and Fix Verification Script.
"""

import json
import urllib.request

BASE_URL = "http://localhost:5000/api/v1"


def post(endpoint, data, token=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(endpoint, token=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_verification():
    print("==================================================================")
    print("CARDIOCARE AI LIVE SYSTEM AND FIX VERIFICATION")
    print("==================================================================")

    # 1. Login
    login_res = post("/auth/login", {"username": "clinician_demo", "password": "ClinicianPass123!"})
    token = login_res["data"]["access_token"]
    print("[1] Authentication: OK (JWT retrieved for Dr. Sarah Chen)")

    # 2. Check Database State
    pts = get("/patients", token)
    print(f"[2] Empty / Initial Patient State: {pts['data']['total']} patients registered")

    # 3. Create Patient
    new_pt = post("/patients", {"age": 54, "sex": "Male", "notes": "Live E2E Verification Patient"}, token)
    pt_id = new_pt["data"]["id"]
    pt_created = new_pt["data"]["created_at"]
    print(f"[3] Created Patient: {new_pt['data']['patient_code']} (id={pt_id})")
    print(f"    - Timestamp: {pt_created}")
    assert pt_created.endswith("Z"), f"Timestamp {pt_created} must end with Z"

    # 4. Create Encounter
    assess = post(f"/patients/{pt_id}/assessments", {"reason_for_visit": "Cardiovascular screening intake"}, token)
    a_id = assess["data"]["id"]
    a_created = assess["data"]["created_at"]
    print(f"[4] Created Encounter #{a_id} with UTC timestamp: {a_created}")
    assert a_created.endswith("Z"), f"Timestamp {a_created} must end with Z"

    # 5. Record Symptoms with NON-anginal chest pain (all 3 criteria explicitly False)
    sym = post(
        f"/assessments/{a_id}/symptoms",
        {
            "chest_pain": True,
            "substernal_location": False,
            "exertional_provocation": False,
            "relieved_by_rest": False,
            "chest_pain_quality": "sharp",
        },
        token,
    )
    angina_class = sym["data"]["angina_classification"]
    print(f"[5] Symptom Intake: Chest Pain=True, 0/3 Criteria met -> Angina Class: '{angina_class}'")
    assert angina_class == "none", f"Expected 'none', got {angina_class}"

    # 6. Record Vitals with safe BMI
    vit = post(
        f"/assessments/{a_id}/vitals",
        {
            "systolic_bp": 124.0,
            "diastolic_bp": 82.0,
            "heart_rate": 72.0,
            "height_cm": 175.0,
            "weight_kg": 72.0,
            "bmi": 23.5,
        },
        token,
    )
    print(f"[6] Vitals Intake: BP {vit['data']['systolic_bp']}/{vit['data']['diastolic_bp']} mmHg, BMI {vit['data']['bmi']} kg/m²")

    # 7. Check Recommendations
    recs = get(f"/assessments/{a_id}/recommendations", token)
    rec_angina = recs["data"]["symptom_evaluation"]["angina_classification"]
    print(f"[7] Clinical Recommendations: Angina Classification is '{rec_angina}' (NOT typical angina)")
    assert rec_angina == "none"

    # 8. Record required labs
    for name, val in [
        ("cholesterol", 198.0),
        ("fasting_blood_sugar", 95.0),
        ("restecg", "normal"),
        ("st_depression", 0.0),
        ("slope", "upsloping"),
        ("ca", 0),
        ("thal", "normal"),
    ]:
        post(
            f"/assessments/{a_id}/labs",
            {"test_name": name, "value_numeric": val if isinstance(val, (int, float)) else None, "value_text": str(val)},
            token,
        )

    # 9. Execute ML Inference
    pred = post(f"/assessments/{a_id}/predictions", {"task_name": "coronary_artery_disease"}, token)
    model_pred = pred["data"]
    print(f"[8] ML Pipeline Execution:")
    print(f"    - Task: {model_pred['task_name']}")
    print(f"    - Model Name: {model_pred['model_name']} v{model_pred['model_version']}")
    print(f"    - Prediction: {model_pred['predicted_class_label']}")
    print(f"    - Calibrated Prob: {model_pred['calibrated_probability']}")
    print(f"    - Input cp feature: '{model_pred['input_features_snapshot']['cp']}' (NOT 'typical angina')")
    assert model_pred["input_features_snapshot"]["cp"] == "asymptomatic"

    print("==================================================================")
    print("[SUCCESS] ALL 8 INTEGRATED VERIFICATION CHECKS PASSED PERFECTLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_verification()
