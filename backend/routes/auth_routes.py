"""
Authentication Routes.

Endpoints:
- POST   /api/v1/auth/register : Create a new user account with hashed credentials.
- POST   /api/v1/auth/login    : Validate credentials and issue JWT session token.
- POST   /api/v1/auth/logout   : Terminate current session.
- GET    /api/v1/auth/me       : Retrieve profile of current authenticated user.
- DELETE /api/v1/auth/me       : Permanently delete current authenticated account after reauthentication.
"""

from flask import Blueprint
from backend.schemas.auth_schemas import (
    DeleteAccountRequestSchema,
    LoginRequestSchema,
    RegisterRequestSchema,
)
from backend.services.auth_service import AuthService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import get_current_user, jwt_required
from backend.extensions import db
from database.models import User

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
@validate_schema(RegisterRequestSchema)
def register(validated_data: RegisterRequestSchema):
    """Register a new user account with secure password hashing."""
    result, err = AuthService.register(
        full_name=validated_data.full_name,
        email=validated_data.email,
        password=validated_data.password,
        role=validated_data.role or "patient",
    )
    if err == "email_exists":
        return api_error(
            409,
            "Conflict",
            "An account with this email already exists. Please log in.",
        )
    if err:
        return api_error(
            400,
            "Bad Request",
            f"Registration failed: {err}",
        )

    return api_response(
        data=result,
        message="Account created successfully.",
        status_code=201,
    )


@auth_bp.route("/login", methods=["POST"])
@validate_schema(LoginRequestSchema)
def login(validated_data: LoginRequestSchema):
    """Authenticate credentials and generate JWT session token."""
    result, err = AuthService.login(
        username_or_email=validated_data.username,
        password=validated_data.password,
    )
    if err == "user_not_found":
        return api_error(
            401,
            "Unauthorized",
            "No account found. Please create an account.",
        )
    if err == "invalid_password":
        return api_error(
            401,
            "Unauthorized",
            "Incorrect password. Please verify your credentials and retry.",
        )
    if err == "inactive":
        return api_error(
            401,
            "Unauthorized",
            "Account has been deactivated or disabled.",
        )
    if not result:
        return api_error(
            401,
            "Unauthorized",
            "Invalid credentials. Please verify your username and password.",
        )

    return api_response(
        data=result,
        message="Authentication successful.",
        status_code=200,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Terminate the current authentication session."""
    return api_response(
        data={"logged_out": True},
        message="Logged out successfully.",
        status_code=200,
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return user profile from verified JWT session and database record."""
    user_claims = get_current_user()
    if not user_claims:
        return api_error(401, "Unauthorized", "No active user session.")

    user_id = user_claims.get("sub")
    if user_id and str(user_id).isdigit():
        user = db.session.get(User, int(user_id))
        if user:
            return api_response(
                data=user.to_dict(),
                message="Session active.",
                status_code=200,
            )

    # Fallback to claims if user object not in DB
    return api_response(
        data=user_claims,
        message="Session active.",
        status_code=200,
    )


@auth_bp.route("/me", methods=["DELETE"])
@jwt_required()
@validate_schema(DeleteAccountRequestSchema)
def delete_account(validated_data: DeleteAccountRequestSchema):
    """
    Permanently delete the current authenticated account.

    Requires password reauthentication. Account identity is derived strictly
    from the validated JWT token, preventing manipulation of target account ID.
    """
    user_claims = get_current_user()
    if not user_claims:
        return api_error(401, "Unauthorized", "Authentication required.")

    user_id_raw = user_claims.get("sub")
    if not user_id_raw or not str(user_id_raw).isdigit():
        return api_error(400, "Bad Request", "Invalid account identity in token.")

    user_id = int(user_id_raw)
    success, err = AuthService.delete_account(
        user_id=user_id,
        password=validated_data.password,
    )

    if err == "user_not_found":
        return api_error(404, "Not Found", "Account record not found.")
    if err == "invalid_password":
        return api_error(
            401,
            "Unauthorized",
            "Incorrect password. Account deletion requires valid password reauthentication.",
        )
    if not success:
        return api_error(500, "Internal Server Error", f"Failed to delete account: {err}")

    return api_response(
        data={"deleted": True},
        message="Your account has been deleted permanently.",
        status_code=200,
    )
