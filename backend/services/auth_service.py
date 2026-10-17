"""
Authentication Service.

Manages user credential verification and JWT generation.
"""

from typing import Any, Dict, Optional
from werkzeug.security import check_password_hash

from backend.utils.security import DEMO_USERS, generate_jwt_token


class AuthService:
    """Authentication and identity operations."""

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify username and password against demo/configured user store."""
        user = DEMO_USERS.get(username)
        if not user or not user.get("is_active"):
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        return user

    @classmethod
    def login(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Perform login and return token with profile metadata."""
        user = cls.authenticate(username, password)
        if not user:
            return None

        token = generate_jwt_token(user)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_hours": 24,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "name": user["name"],
                "email": user.get("email"),
                "patient_id": user.get("patient_id"),
            },
        }
