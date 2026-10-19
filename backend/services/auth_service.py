"""
Authentication Service.

Manages user registration, credential verification, JWT generation, and account deletion.
"""

from typing import Any, Dict, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from backend.extensions import db
from database.models import User
from backend.utils.security import DEMO_USERS, generate_jwt_token


class AuthService:
    """Authentication, registration, and identity lifecycle operations."""

    @staticmethod
    def register(
        full_name: str,
        email: str,
        password: str,
        role: str = "patient",
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Create and persist a new user account.

        Returns
        -------
        Tuple[Optional[Dict[str, Any]], Optional[str]]
            (user_dict_and_token, error_code)
            error_code is "email_exists" if duplicate email.
        """
        norm_email = (email or "").strip().lower()
        if not norm_email:
            return None, "invalid_email"

        # Check existing user in database
        existing = User.query.filter(func.lower(User.email) == norm_email).first()
        if existing:
            return None, "email_exists"

        # Determine username prefix
        username_candidate = norm_email.split("@")[0]
        existing_username = User.query.filter(func.lower(User.username) == username_candidate).first()
        if existing_username:
            username_candidate = f"{username_candidate}_{int(func.random() * 1000)}"

        user = User(
            full_name=full_name.strip(),
            email=norm_email,
            username=username_candidate,
            role=role if role in ("patient", "clinician", "admin") else "patient",
            is_active=True,
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None, "email_exists"
        except Exception as e:
            db.session.rollback()
            return None, f"database_error: {str(e)}"

        token = generate_jwt_token(user.to_dict())
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_hours": 24,
            "user": user.to_dict(),
        }, None

    @staticmethod
    def authenticate(username_or_email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify username or email and password.

        Returns
        -------
        Tuple[Optional[Dict[str, Any]], Optional[str]]
            (user_dict, error_code)
            error_code is "user_not_found", "invalid_password", or "inactive".
        """
        norm_identifier = (username_or_email or "").strip().lower()
        if not norm_identifier:
            return None, "user_not_found"

        user = User.query.filter(
            (func.lower(User.username) == norm_identifier) | (func.lower(User.email) == norm_identifier)
        ).first()

        if not user:
            # Fallback for mock demo tests
            demo = DEMO_USERS.get(norm_identifier)
            if demo:
                if not demo.get("is_active"):
                    return None, "inactive"
                if not check_password_hash(demo["password_hash"], password):
                    return None, "invalid_password"
                return demo, None
            return None, "user_not_found"

        if not user.is_active:
            return None, "inactive"

        if not user.check_password(password):
            return None, "invalid_password"

        return user.to_dict(), None

    @classmethod
    def login(cls, username_or_email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate credentials and issue JWT token with user profile.

        Returns
        -------
        Tuple[Optional[Dict[str, Any]], Optional[str]]
            (response_dict, error_code)
        """
        user_dict, err = cls.authenticate(username_or_email, password)
        if not user_dict:
            return None, err

        token = generate_jwt_token(user_dict)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_hours": 24,
            "user": {
                "id": user_dict["id"],
                "username": user_dict["username"],
                "role": user_dict["role"],
                "name": user_dict.get("name") or user_dict.get("full_name"),
                "full_name": user_dict.get("full_name") or user_dict.get("name"),
                "email": user_dict.get("email"),
                "patient_id": user_dict.get("patient_id"),
            },
        }, None

    @staticmethod
    def delete_account(user_id: int, password: str) -> Tuple[bool, Optional[str]]:
        """
        Permanently delete the user's account after verifying current password.

        Returns
        -------
        Tuple[bool, Optional[str]]
            (success, error_code)
        """
        user = db.session.get(User, user_id)
        if not user:
            return False, "user_not_found"

        if not user.check_password(password):
            return False, "invalid_password"

        try:
            db.session.delete(user)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"database_error: {str(e)}"
