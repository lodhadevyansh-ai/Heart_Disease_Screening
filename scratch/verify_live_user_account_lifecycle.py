"""
Live End-to-End Account Management Verification Script.

Tests against live Flask server:
1. Register new user (POST /auth/register) -> 201 Created
2. Reject duplicate registration with same email -> 409 Conflict
3. Reject login with wrong password -> 401 Unauthorized
4. Reject login with nonexistent user -> 401 Unauthorized
5. Log in with registered user (POST /auth/login) -> 200 OK
6. Access protected profile (GET /auth/me) -> 200 OK
7. Reject deletion with incorrect password -> 401 Unauthorized
8. Delete account permanently (DELETE /auth/me) -> 200 OK
9. Reject protected access with revoked token -> 401 Unauthorized
10. Reject subsequent login with former credentials -> 401 Unauthorized
"""

import sys
import uuid
import requests

BASE_URL = "http://127.0.0.1:5000/api/v1"

def run_live_verification():
    print("=" * 70)
    print("RUNNING LIVE END-TO-END USER ACCOUNT MANAGEMENT VERIFICATION")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    unique_suffix = str(uuid.uuid4())[:8]
    test_email = f"user_{unique_suffix}@live.demo"
    test_password = "LivePassword123!"
    test_name = f"Live Test User {unique_suffix}"

    # 1. Register new account
    print(f"\n1. Testing Account Creation (Sign Up) for {test_email}...")
    reg_payload = {
        "full_name": test_name,
        "email": test_email,
        "password": test_password,
        "confirm_password": test_password,
        "role": "patient",
    }
    r = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    print(f"   Status: {r.status_code}")
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    reg_data = r.json()
    assert reg_data["status"] == "success"
    assert "access_token" in reg_data["data"]
    token = reg_data["data"]["access_token"]
    user_id = reg_data["data"]["user"]["id"]
    print(f"   [OK] Account created successfully (User ID: {user_id}). Token received.")

    # 2. Reject duplicate email
    print("\n2. Testing Duplicate Email Rejection...")
    dup_r = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    print(f"   Status: {dup_r.status_code}")
    assert dup_r.status_code == 409, f"Expected 409, got {dup_r.status_code}: {dup_r.text}"
    dup_err = dup_r.json()["error"]["message"]
    print(f"   [OK] Duplicate email rejected: \"{dup_err}\"")

    # 3. Reject login with wrong password
    print("\n3. Testing Login with Incorrect Password...")
    bad_pass_r = requests.post(f"{BASE_URL}/auth/login", json={"username": test_email, "password": "WrongPassword999!"})
    print(f"   Status: {bad_pass_r.status_code}")
    assert bad_pass_r.status_code == 401
    bad_pass_msg = bad_pass_r.json()["error"]["message"]
    print(f"   [OK] Incorrect password rejected: \"{bad_pass_msg}\"")

    # 4. Reject login with nonexistent account
    print("\n4. Testing Login with Nonexistent Account...")
    no_acct_r = requests.post(f"{BASE_URL}/auth/login", json={"username": "never_existed@hospital.demo", "password": "Password123!"})
    print(f"   Status: {no_acct_r.status_code}")
    assert no_acct_r.status_code == 401
    no_acct_msg = no_acct_r.json()["error"]["message"]
    print(f"   [OK] Nonexistent account rejected: \"{no_acct_msg}\"")

    # 5. Log in with valid credentials
    print("\n5. Testing Login with Valid Credentials...")
    login_r = requests.post(f"{BASE_URL}/auth/login", json={"username": test_email, "password": test_password})
    print(f"   Status: {login_r.status_code}")
    assert login_r.status_code == 200
    login_data = login_r.json()["data"]
    assert "access_token" in login_data
    session_token = login_data["access_token"]
    print(f"   [OK] Login successful. Session token verified.")

    # 6. Access protected /auth/me
    print("\n6. Testing Protected Session Verification (GET /auth/me)...")
    headers = {"Authorization": f"Bearer {session_token}"}
    me_r = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"   Status: {me_r.status_code}")
    assert me_r.status_code == 200
    me_data = me_r.json()["data"]
    assert me_data["email"] == test_email
    print(f"   [OK] Session active for: {me_data['full_name']} ({me_data['email']})")

    # 7. Reject deletion with wrong password
    print("\n7. Testing Account Deletion with Wrong Password...")
    bad_del_r = requests.delete(f"{BASE_URL}/auth/me", json={"password": "WrongPassword99!"}, headers=headers)
    print(f"   Status: {bad_del_r.status_code}")
    assert bad_del_r.status_code == 401
    print(f"   [OK] Deletion rejected without correct password: \"{bad_del_r.json()['error']['message']}\"")

    # 8. Permanently delete account
    print("\n8. Testing Permanent Account Deletion (DELETE /auth/me)...")
    del_r = requests.delete(f"{BASE_URL}/auth/me", json={"password": test_password}, headers=headers)
    print(f"   Status: {del_r.status_code}")
    assert del_r.status_code == 200
    assert del_r.json()["data"]["deleted"] is True
    print(f"   [OK] Account deleted: \"{del_r.json()['message']}\"")

    # 9. Verify old token is rejected
    print("\n9. Testing Old Token Invalidation on Protected Endpoints...")
    old_token_r = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print(f"   Status: {old_token_r.status_code}")
    assert old_token_r.status_code == 401
    print(f"   [OK] Revoked token rejected: \"{old_token_r.json()['error']['message']}\"")

    # 10. Verify subsequent login fails
    print("\n10. Testing Subsequent Login Attempt with Deleted Account...")
    post_del_login = requests.post(f"{BASE_URL}/auth/login", json={"username": test_email, "password": test_password})
    print(f"   Status: {post_del_login.status_code}")
    assert post_del_login.status_code == 401
    print(f"   [OK] Former credentials rejected: \"{post_del_login.json()['error']['message']}\"")

    print("\n" + "=" * 70)
    print("ALL 10 LIVE USER ACCOUNT MANAGEMENT CHECKS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_live_verification()
    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
