"""
API Error Handlers and Consistent Response Utilities.

Provides standardized JSON response wrappers and schema validation helpers
for API endpoints.
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from flask import jsonify, request, Response
from pydantic import BaseModel, ValidationError as PydanticValidationError
from werkzeug.exceptions import HTTPException

T = TypeVar("T", bound=BaseModel)


def api_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
) -> Response:
    """Generate a consistent JSON success response."""
    payload: Dict[str, Any] = {
        "status": "success",
    }
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if meta is not None:
        payload["meta"] = meta

    return jsonify(payload), status_code


def api_error(
    code: int,
    name: str,
    message: str,
    details: Optional[Any] = None,
) -> Response:
    """Generate a consistent JSON error response."""
    payload: Dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "name": name,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details

    return jsonify(payload), code


def validate_schema(schema_cls: Type[T]) -> Callable:
    """
    Decorator to parse and validate incoming request JSON using Pydantic.
    Passes validated schema instance as `validated_data` keyword argument to the view.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            raw_data = request.get_json(silent=True)
            if raw_data is None:
                if request.content_length and request.content_length > 0:
                    return api_error(400, "Bad Request", "Malformed JSON body.")
                raw_data = {}

            try:
                validated = schema_cls.model_validate(raw_data)
            except PydanticValidationError as e:
                errors = []
                for err in e.errors():
                    field_loc = " -> ".join(str(loc) for loc in err["loc"])
                    errors.append({
                        "field": field_loc,
                        "message": err["msg"],
                        "type": err["type"],
                    })
                return api_error(
                    422,
                    "Unprocessable Entity",
                    "Input validation failed. Please check field requirements and clinical constraints.",
                    details=errors,
                )
            except Exception as e:
                return api_error(400, "Bad Request", f"Schema validation error: {str(e)}")

            kwargs["validated_data"] = validated
            return fn(*args, **kwargs)
        return wrapper
    return decorator
