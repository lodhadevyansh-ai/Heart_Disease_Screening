"""
Common Schemas and Pagination Parameters.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel):
    """Envelope for paginated query results."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int
