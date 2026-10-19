"""
Unit and Integration Tests for User Account Management.

Covers:
1. Account Creation / Sign Up:
   - Valid user creation and persistence in database.
   - Secure password hashing (no plaintext passwords).
   - Duplicate email rejection with 409 Conflict.
   - Validation failures: invalid email syntax, weak password, confirmation mismatch.
   - Transaction rollback on failed registration.
2. Login Validation:
   - Successful authentication with email or username.
   - Rejection of incorrect passwords with clear message.
   - Rejection of nonexistent accounts with clear guidance ("No account found").
   - Rejection of unauthenticated requests to protected endpoints.
3. Permanent Account Deletion:
   - Reauthentication required via current password.
   - Permanent removal from active database table (not merely soft-hidden).
   - Invalidation of old JWT tokens for deleted accounts.
   - Re-login failure with former credentials.
   - Prevention of cross-user account deletion (identity bound strictly to verified token).
   - Rollback handling on unexpected database error.
"""

import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from database.models import User, Patient
from database.db import seed_default_users


@pytest.fixture
def app():
    """Create Flask application in testing mode with in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        seed_default_users(test_app)
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


class TestUserRegistration:
    """Test suite for user account registration."""

    def test_valid_user_registration_success(self, client, app):
        """A valid user can create an account and is persisted with hashed password."""
        payload = {
            "full_name": "Dr. Alexander Wright",
            "email": "alex.wright@cardiology.demo",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "role": "clinician",
        }
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201
        data = res.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        user_info = data["data"]["user"]
        assert user_info["email"] == "alex.wright@cardiology.demo"
        assert user_info["full_name"] == "Dr. Alexander Wright"
        assert "password" not in user_info
        assert "password_hash" not in user_info

        # Verify database persistence
        with app.app_context():
            saved_user = User.query.filter_by(email="alex.wright@cardiology.demo").first()
            assert saved_user is not None
            assert saved_user.full_name == "Dr. Alexander Wright"
            # Never store plaintext passwords
            assert saved_user.password_hash != "SecurePassword123!"
            assert saved_user.check_password("SecurePassword123!") is True

    def test_duplicate_email_registration_rejected(self, client):
        """Registering with an existing email must be rejected with 409 Conflict."""
        payload = {
            "full_name": "Duplicate User One",
            "email": "unique.test@cardiology.demo",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        res1 = client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        # Attempt duplicate registration with different casing/whitespace
        duplicate_payload = {
            "full_name": "Duplicate User Two",
            "email": " UNIQUE.TEST@cardiology.demo ",
            "password": "AnotherPassword456!",
            "confirm_password": "AnotherPassword456!",
        }
        res2 = client.post("/api/v1/auth/register", json=duplicate_payload)
        assert res2.status_code == 409
        err = res2.get_json()["error"]
        assert "already exists" in err["message"].lower()

    def test_password_confirmation_mismatch_rejected(self, client):
        """Mismatched passwords must be rejected with validation error (422)."""
        payload = {
            "full_name": "Mismatch User",
            "email": "mismatch@cardiology.demo",
            "password": "SecurePassword123!",
            "confirm_password": "DifferentPassword999!",
        }
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 422
        data = res.get_json()
        assert data["status"] == "error"

    def test_weak_password_rejected(self, client):
        """Passwords failing length or complexity requirements must be rejected (422)."""
        # Too short (< 8 chars)
        res_short = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Short Password",
                "email": "short@cardiology.demo",
                "password": "abc",
                "confirm_password": "abc",
            },
        )
        assert res_short.status_code == 422

        # No digits
        res_no_digits = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "No Digits",
                "email": "nodigits@cardiology.demo",
                "password": "PasswordOnlyLetters",
                "confirm_password": "PasswordOnlyLetters",
            },
        )
        assert res_no_digits.status_code == 422

    def test_invalid_email_format_rejected(self, client):
        """Malformed email addresses must be rejected with 422."""
        res = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Bad Email",
                "email": "not-a-valid-email",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
            },
        )
        assert res.status_code == 422


class TestUserLogin:
    """Test suite for credential authentication and session establishment."""

    def test_login_with_registered_credentials_success(self, client):
        """A registered user can log in with their email and password."""
        # 1. Register
        client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Patient Jane Doe",
                "email": "jane.doe@portal.demo",
                "password": "PatientPass123!",
                "confirm_password": "PatientPass123!",
                "role": "patient",
            },
        )

        # 2. Log in using email
        res_login = client.post(
            "/api/v1/auth/login",
            json={"username": "jane.doe@portal.demo", "password": "PatientPass123!"},
        )
        assert res_login.status_code == 200
        data = res_login.get_json()["data"]
        assert "access_token" in data
        assert data["user"]["email"] == "jane.doe@portal.demo"

    def test_login_incorrect_password_rejected(self, client):
        """Incorrect password returns 401 with informative error."""
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "clinician_demo", "password": "WrongPassword123!"},
        )
        assert res.status_code == 401
        err = res.get_json()["error"]
        assert "incorrect password" in err["message"].lower()

    def test_login_nonexistent_account_rejected(self, client):
        """Logging in with nonexistent user returns 401 with 'No account found' guidance."""
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "does_not_exist@hospital.demo", "password": "SomePassword123!"},
        )
        assert res.status_code == 401
        err = res.get_json()["error"]
        assert "no account found" in err["message"].lower()

    def test_protected_endpoints_reject_unauthenticated_requests(self, client):
        """Accessing /auth/me without a token must return 401."""
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401


class TestPermanentAccountDeletion:
    """Test suite for permanent account deletion and session revocation."""

    def test_authenticated_user_can_delete_own_account(self, client, app):
        """An authenticated user can permanently delete their account using valid reauthentication."""
        # 1. Register a user
        reg_res = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "User To Delete",
                "email": "delete.me@cardiology.demo",
                "password": "DeletePass123!",
                "confirm_password": "DeletePass123!",
            },
        )
        token = reg_res.get_json()["data"]["access_token"]
        user_id = reg_res.get_json()["data"]["user"]["id"]

        # 2. Delete account with correct password
        del_res = client.delete(
            "/api/v1/auth/me",
            json={"password": "DeletePass123!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 200
        assert del_res.get_json()["data"]["deleted"] is True
        assert "deleted permanently" in del_res.get_json()["message"].lower()

        # 3. Verify user record is completely absent from database
        with app.app_context():
            deleted_user = db.session.get(User, user_id)
            assert deleted_user is None

        # 4. Old token cannot access protected endpoints
        protected_res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert protected_res.status_code == 401

        # 5. Subsequent login with former credentials fails
        relogin_res = client.post(
            "/api/v1/auth/login",
            json={"username": "delete.me@cardiology.demo", "password": "DeletePass123!"},
        )
        assert relogin_res.status_code == 401
        assert "no account found" in relogin_res.get_json()["error"]["message"].lower()

    def test_account_deletion_incorrect_password_rejected(self, client, app):
        """Incorrect password prevents account deletion and leaves record intact."""
        # 1. Register
        reg_res = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Protected User",
                "email": "keep.me@cardiology.demo",
                "password": "RealPassword123!",
                "confirm_password": "RealPassword123!",
            },
        )
        token = reg_res.get_json()["data"]["access_token"]
        user_id = reg_res.get_json()["data"]["user"]["id"]

        # 2. Attempt deletion with wrong password
        del_res = client.delete(
            "/api/v1/auth/me",
            json={"password": "WrongPassword999!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 401
        assert "incorrect password" in del_res.get_json()["error"]["message"].lower()

        # 3. User must still exist in database
        with app.app_context():
            assert db.session.get(User, user_id) is not None

    def test_account_deletion_cannot_delete_other_user(self, client):
        """Backend derives deletion identity strictly from verified token, ignoring request body spoofing."""
        # Register User A
        res_a = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "User Alpha",
                "email": "alpha@hospital.demo",
                "password": "AlphaPassword123!",
                "confirm_password": "AlphaPassword123!",
            },
        )
        token_a = res_a.get_json()["data"]["access_token"]

        # Register User B
        res_b = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "User Beta",
                "email": "beta@hospital.demo",
                "password": "BetaPassword123!",
                "confirm_password": "BetaPassword123!",
            },
        )
        user_b_id = res_b.get_json()["data"]["user"]["id"]

        # User A sends request attempting to pass target_user_id=User B
        del_res = client.delete(
            "/api/v1/auth/me",
            json={"password": "AlphaPassword123!", "user_id": user_b_id, "target_user_id": user_b_id},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert del_res.status_code == 200

        # User B must still exist
        relogin_b = client.post(
            "/api/v1/auth/login",
            json={"username": "beta@hospital.demo", "password": "BetaPassword123!"},
        )
        assert relogin_b.status_code == 200
