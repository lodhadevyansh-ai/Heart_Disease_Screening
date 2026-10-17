"""
Authentication Routes.

Endpoints:
- POST /api/v1/auth/login : Issue JWT token for verified credentials.
- GET  /api/v1/auth/me    : Retrieve profile of current authenticated user.
"""

from flask import Blueprint
from backend.schemas.auth_schemas import LoginRequestSchema
from backend.services.auth_service import AuthService
from backend.utils.error_handlers import api_error, api_response, validate_schema
from backend.utils.security import get_current_user, jwt_required

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
@validate_schema(LoginRequestSchema)
def login(validated_data: LoginRequestSchema):
    """Authenticate credentials and generate JWT token."""
    result = AuthService.login(
        username=validated_data.username,
        password=validated_data.password,
    )
    if not result:
        return api_error(
            401,
            "Unauthorized",
            "Invalid username or password. Check credentials and retry.",
        )

    return api_response(
        data=result,
        message="Authentication successful.",
        status_code=200,
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return user claims from current JWT session."""
    user = get_current_user()
    if not user:
        return api_error(401, "Unauthorized", "No active user session.")

    return api_response(
        data=user,
        message="Session active.",
        status_code=200,
    )
