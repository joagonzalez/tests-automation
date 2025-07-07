"""API endpoints package."""

from . import (
    health,
    test_runs,
    test_types,
    environments,
    results,
    upload,
)

__all__ = [
    "health",
    "test_runs",
    "test_types",
    "environments",
    "results",
    "upload",
]
