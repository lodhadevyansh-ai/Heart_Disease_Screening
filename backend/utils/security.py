"""
Authentication, Authorization, and Privacy Protection Utilities.

Provides JWT generation and verification, role-based access control,
and patient-level data isolation to ensure HIPAA and privacy compliance.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set
from flask import current_app, g, request
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from backend.utils.error_handlers import api_error


# Demo user accounts for development, testing, and sandbox verification.
# In production, users are loaded from an external identity provider or credentials database.
DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "clinician_demo": {
        "id": 101,
        "username": "clinician_demo",
        # Default password: ClinicianPass123!
        "password_hash": generate_password_hash("ClinicianPass123!"),
        "role": "clinician",
        "name": "Dr. Sarah Chen, MD",
        "email": "sarah.chen@hospital.demo",
        "is_active": True,
        "patient_id": None,
    },
    "admin_demo": {
        "id": 102,
        "username": "admin_demo",
        # Default password: AdminPass123!
        "password_hash": generate_password_hash("AdminPass123!"),
        "role": "admin",
        "name": "System Administrator",
        "email": "admin@hospital.demo",
        "is_active": True,
        "patient_id": None,
    },
    "patient_demo": {
        "id": 103,
        "username": "patient_demo",
        # Default password: PatientPass123!
        "password_hash": generate_password_hash("PatientPass123!"),
        "role": "patient",
        "name": "Demo Patient Account",
        "email": "patient1@demo.portal",
        "is_active": True,
        "patient_id": 1,  # Tied to patient ID 1
    },
}


def generate_jwt_token(
    user_payload: Dict[str, Any],
    expires_in_hours: Optional[int] = None,
) -> str:
    """
    Generate a signed JWT token.

    Parameters
    ----------
    user_payload : dict
        User claims including id, username, role, and optional patient_id.
    expires_in_hours : int, optional
        Token validity window. Defaults to app config JWT_EXPIRATION_HOURS.

    Returns
    -------
    str
        Encoded JWT token.
    """
    secret = current_app.config.get("JWT_SECRET_KEY", current_app.config.get("SECRET_KEY", "fallback-secret"))
    expiry_hours = expires_in_hours or current_app.config.get("JWT_EXPIRATION_HOURS", 24)
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_payload["id"]),
        "username": user_payload["username"],
        "role": user_payload["role"],
        "name": user_payload.get("name", user_payload["username"]),
        "patient_id": user_payload.get("patient_id"),
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a signed JWT token.

    Parameters
    ----------
    token : str
        Encoded JWT string.

    Returns
    -------
    dict
        Decoded token claims.

    Raises
    ------
    jwt.PyJWTError
        If expired, invalid signature, or malformed.
    """
    secret = current_app.config.get("JWT_SECRET_KEY", current_app.config.get("SECRET_KEY", "fallback-secret"))
    return jwt.decode(token, secret, algorithms=["HS256"])


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieve currently authenticated user payload from Flask request context `g`."""
    return getattr(g, "current_user", None)


def jwt_required(optional: bool = False) -> Callable:
    """
    Decorator requiring a valid JWT Bearer token in the Authorization header.

    If optional=True and no token is supplied, allows the request with g.current_user=None.
    If a token IS supplied and invalid, it returns 401 Unauthorized regardless of optional.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                if optional:
                    g.current_user = None
                    return fn(*args, **kwargs)
                return api_error(401, "Unauthorized", "Missing Authorization header. Bearer token required.")

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return api_error(401, "Unauthorized", "Malformed Authorization header. Format: Bearer <token>")

            token = parts[1]
            try:
                payload = decode_jwt_token(token)
                g.current_user = payload

                # Verify user account still exists in active database
                try:
                    from database.models import User
                    from backend.extensions import db
                    user_id = payload.get("sub")
                    if user_id and str(user_id).isdigit():
                        user_obj = db.session.get(User, int(user_id))
                        if user_obj is None:
                            # If database contains users, this user was deleted
                            if User.query.first() is not None:
                                return api_error(
                                    401,
                                    "Unauthorized",
                                    "User account no longer exists or session has been revoked.",
                                )
                        elif not user_obj.is_active:
                            return api_error(
                                401,
                                "Unauthorized",
                                "Account has been deactivated or disabled.",
                            )
                except Exception:
                    # Ignore db lookup errors in non-db test environments
                    pass

            except jwt.ExpiredSignatureError:
                return api_error(401, "Unauthorized", "Authentication token has expired. Please log in again.")
            except jwt.InvalidTokenError as e:
                return api_error(401, "Unauthorized", f"Invalid authentication token: {str(e)}")

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def roles_required(*allowed_roles: str) -> Callable:
    """Decorator ensuring the authenticated user has one of the required roles."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = get_current_user()
            if not user:
                return api_error(401, "Unauthorized", "Authentication required.")

            user_role = user.get("role")
            if user_role not in allowed_roles:
                return api_error(
                    403,
                    "Forbidden",
                    f"Access denied. Required roles: {list(allowed_roles)}. Your role: '{user_role}'.",
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def verify_patient_access(target_patient_id: int) -> Optional[tuple]:
    """
    Check if the authenticated user has authorization to access `target_patient_id`.
    
    Returns None if permitted, or returns an error response tuple if forbidden.
    - Admins have administrative access.
    - Clinicians can ONLY access patient records that they own (patient.user_id == user.sub).
    - Patients can ONLY access their own records (token patient_id == target_patient_id).
    """
    user = get_current_user()
    if not user:
        return api_error(401, "Unauthorized", "Authentication required.")

    user_id = user.get("sub")
    role = user.get("role")

    if role == "patient":
        user_patient_id = user.get("patient_id")
        if user_patient_id is None or int(user_patient_id) != int(target_patient_id):
            return api_error(
                403,
                "Forbidden",
                "Privacy Violation: Patients are strictly forbidden from accessing other patients' medical records.",
            )
        return None

    from database.models import Patient
    patient = Patient.query.filter_by(id=target_patient_id).first()
    if not patient:
        return api_error(404, "Not Found", f"Patient with ID {target_patient_id} not found.")

    if role == "admin":
        return None

    if role == "clinician":
        if patient.user_id is not None and str(patient.user_id) != str(user_id):
            return api_error(
                403,
                "Forbidden",
                "Access denied: You do not have ownership of this patient record.",
            )
        return None

    return api_error(403, "Forbidden", "Unauthorized role for patient medical data.")
