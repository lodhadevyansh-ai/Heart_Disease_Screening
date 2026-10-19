"""
API Test Suite (tests/test_api.py).

Validates API contracts, response schemas, error formatting, CORS,
and endpoints across all modules.
"""

import io
import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.tests.test_backend_foundation import (
    TestFlaskBackendFoundation,
    TestErrorHandlers,
    TestCorsConfiguration,
    TestLoggingSecurity,
)
from backend.tests.test_api_endpoints import (
    TestAuthenticationEndpoints,
    TestPatientEndpointsAndPrivacy,
    TestAssessmentSymptomsAndVitals,
    TestDocumentUploadAndStructuredLabs,
    TestClinicalRecommendationsAndSafety,
    TestMachineLearningPredictionEndpoints,
    TestResilientErrorAndDatabaseHandling,
)

# Export all test classes so running `pytest tests/test_api.py` executes all API test suites
__all__ = [
    "TestFlaskBackendFoundation",
    "TestErrorHandlers",
    "TestCorsConfiguration",
    "TestLoggingSecurity",
    "TestAuthenticationEndpoints",
    "TestPatientEndpointsAndPrivacy",
    "TestAssessmentSymptomsAndVitals",
    "TestDocumentUploadAndStructuredLabs",
    "TestClinicalRecommendationsAndSafety",
    "TestMachineLearningPredictionEndpoints",
    "TestResilientErrorAndDatabaseHandling",
]
