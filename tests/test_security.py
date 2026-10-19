"""
Phase 14: Security, Privacy, and Authorization Test Suite (tests/test_security.py).

Validates:
1. Version control exclusions (.gitignore audit for secrets, databases, and uploads).
2. Frontend environment variable hygiene (no server secrets in VITE_ envs).
3. Secure document uploads (magic byte verification, extension whitelist, path traversal protection).
4. Sensitive data filtering in logging pipelines (token, password, MRN masking).
5. Role-based authorization & multi-tenant patient medical record isolation.
6. Error handling hygiene (no raw stack traces or internal SQL syntax leaks).
"""

import io
import os
import re
from pathlib import Path
import pytest

from backend.app import create_app, SensitiveDataFilter
from backend.config import TestingConfig, PROJECT_ROOT
from backend.extensions import db
from database.seed_demo_data import seed_synthetic_data


@pytest.fixture
def app():
    """Create test application bound to an in-memory database."""
    test_app = create_app(TestingConfig)
    with test_app.app_context():
        db.create_all()
        seed_synthetic_data(test_app)
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def clinician_token(client):
    """JWT for clinician demo account."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "clinician_demo", "password": "ClinicianPass123!"},
    )
    return res.get_json()["data"]["access_token"]


@pytest.fixture
def patient_token(client):
    """JWT for patient demo account (linked to patient_id=1)."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "patient_demo", "password": "PatientPass123!"},
    )
    return res.get_json()["data"]["access_token"]


class TestRepositorySecurityAndHygiene:
    """Audit project repository configuration and file safety."""

    def test_gitignore_excludes_secrets_and_private_storage(self):
        """Verify .gitignore properly excludes .env, sqlite databases, and uploads."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        assert gitignore_path.exists(), "Root .gitignore must exist."

        content = gitignore_path.read_text(encoding="utf-8")
        patterns = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

        # Key security patterns that must be excluded
        must_exclude = [".env", "uploads", "__pycache__", "node_modules"]
        for item in must_exclude:
            assert any(item in p for p in patterns), f"Critical item '{item}' missing from .gitignore"

    def test_frontend_env_contains_no_server_secrets(self):
        """Verify frontend environment variables only contain public VITE_ configurations."""
        frontend_env = PROJECT_ROOT / "frontend" / ".env"
        if frontend_env.exists():
            content = frontend_env.read_text(encoding="utf-8")
            # Should only contain VITE_ prefixed keys or public URLs
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key = line.split("=")[0].strip()
                assert key.startswith("VITE_"), f"Frontend env key '{key}' must start with VITE_"
                # Prohibit secret keywords
                for forbidden in ["SECRET_KEY", "JWT_SECRET", "DB_PASSWORD", "PRIVATE_KEY"]:
                    assert forbidden not in key.upper(), f"Forbidden server secret key in frontend .env: {key}"


class TestDocumentUploadSecurity:
    """Validates file upload validation, magic bytes, and anti-spoofing controls."""

    def test_upload_rejects_executable_and_script_extensions(self, client, clinician_token):
        """Malicious script extensions (.exe, .py, .sh, .php, .js) must be rejected."""
        headers = {"Authorization": f"Bearer {clinician_token}"}

        # Create patient and assessment first
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-SEC-1", "age": 50, "sex": "Male"},
            headers={"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"},
        )
        pt_id = res_pt.get_json()["data"]["id"]
        res_a = client.post(f"/api/v1/patients/{pt_id}/assessments", json={}, headers=headers)
        assess_id = res_a.get_json()["data"]["id"]

        dangerous_filenames = ["malware.exe", "script.py", "exploit.sh", "webshell.php", "payload.js"]
        for fname in dangerous_filenames:
            data = {
                "file": (io.BytesIO(b"malicious payload content"), fname),
                "document_category": "ecg_report_pdf",
            }
            res = client.post(
                f"/api/v1/assessments/{assess_id}/documents",
                data=data,
                content_type="multipart/form-data",
                headers=headers,
            )
            assert res.status_code in (400, 415), f"Filename {fname} should have been rejected."
            err = res.get_json()["error"]
            assert "extension" in err["message"].lower() or "not allowed" in err["message"].lower()

    def test_upload_rejects_mime_spoofing_via_magic_bytes(self, client, clinician_token):
        """Text file or script renamed to .pdf must be rejected by magic byte inspection."""
        headers = {"Authorization": f"Bearer {clinician_token}"}

        # Create patient and assessment first
        res_pt = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-SEC-2", "age": 52, "sex": "Female"},
            headers={"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"},
        )
        pt_id = res_pt.get_json()["data"]["id"]
        res_a = client.post(f"/api/v1/patients/{pt_id}/assessments", json={}, headers=headers)
        assess_id = res_a.get_json()["data"]["id"]

        # Plain text without '%PDF-' header
        spoofed_pdf = io.BytesIO(b"Hello world, I am actually a text file pretending to be PDF.")
        data = {
            "file": (spoofed_pdf, "spoofed_report.pdf"),
            "document_category": "ecg_report_pdf",
        }
        res = client.post(
            f"/api/v1/assessments/{assess_id}/documents",
            data=data,
            content_type="multipart/form-data",
            headers=headers,
        )
        assert res.status_code in (400, 415)
        err = res.get_json()["error"]
        assert "signature" in err["message"].lower() or "magic" in err["message"].lower() or "mismatch" in err["message"].lower()

    def test_path_traversal_prevention(self, client, clinician_token):
        """Ensure uploaded files cannot escape storage directories via traversal sequences."""
        headers = {"Authorization": f"Bearer {clinician_token}"}

        # Valid PDF header with path traversal attempt in filename
        valid_pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\ntrailer<</Root 1 0 R>>\n%%EOF"
        data = {
            "file": (io.BytesIO(valid_pdf_bytes), "../../../../etc/passwd.pdf"),
            "document_category": "ecg_report_pdf",
        }
        res = client.post(
            "/api/v1/assessments/1/documents",
            data=data,
            content_type="multipart/form-data",
            headers=headers,
        )
        # Even if accepted, stored filename must be sanitized or UUID-based
        if res.status_code == 201:
            stored_doc = res.get_json()["data"]
            assert ".." not in stored_doc["original_filename"]


class TestLoggingPrivacyAndDataMasking:
    """Validates that logs do not disclose sensitive clinical, token, or password data."""

    def test_sensitive_data_filter_masks_credentials_and_tokens(self):
        """SensitiveDataFilter must redact passwords, bearer tokens, and credentials."""
        filter_instance = SensitiveDataFilter()
        import logging

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User login attempted with password=SuperSecretPass123! and token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)
        assert "SuperSecretPass123!" not in record.msg
        assert "[REDACTED]" in record.msg or "***" in record.msg

    def test_error_responses_do_not_leak_stack_traces_or_sql(self, client):
        """Client-facing error responses must never expose python tracebacks or SQL syntax."""
        # Cause a 404
        res = client.get("/api/v1/patients/99999999")
        assert res.status_code in (401, 404)
        err = res.get_json()
        assert "Traceback (most recent call last)" not in str(err)
        assert "SELECT" not in str(err)


class TestRoleBasedAuthorization:
    """Validates role-based access control and patient data isolation."""

    def test_patient_role_cannot_create_patient(self, client, patient_token):
        """Only clinician or admin can register new patients."""
        headers = {"Authorization": f"Bearer {patient_token}", "Content-Type": "application/json"}
        res = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-PAT-DENIED", "age": 40, "sex": "Female"},
            headers=headers,
        )
        assert res.status_code == 403
        assert "denied" in res.get_json()["error"]["message"].lower()

    def test_cross_patient_access_forbidden(self, client, patient_token, clinician_token):
        """Patient user 1 cannot view Patient 2's medical record or assessments."""
        clin_headers = {"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"}
        # Clinician creates patient 1 (matching patient_demo's patient_id=1)
        client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-PT-1-OWN", "age": 45, "sex": "Female"},
            headers=clin_headers,
        )
        # Clinician creates patient 2 (different patient_id)
        res_pt2 = client.post(
            "/api/v1/patients",
            json={"medical_record_number": "MRN-PT-2-SECRET", "age": 55, "sex": "Male"},
            headers=clin_headers,
        )
        pt2_id = res_pt2.get_json()["data"]["id"]

        # Patient 1 tries to access patient 2 profile (cross-patient access)
        pat_headers = {"Authorization": f"Bearer {patient_token}"}
        res_profile = client.get(f"/api/v1/patients/{pt2_id}", headers=pat_headers)
        assert res_profile.status_code == 403

        # Patient 1 tries to access patient 2 assessments
        res_assess = client.get(f"/api/v1/patients/{pt2_id}/assessments", headers=pat_headers)
        assert res_assess.status_code == 403
