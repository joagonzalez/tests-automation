"""
Benchmark Analyzer API - REST API for benchmark data management.

This package provides a FastAPI-based REST API for managing benchmark test results,
environments, and related data. It includes:

- RESTful endpoints for CRUD operations
- Database services and connection management
- Configuration management
- Request/response validation
- Authentication and authorization
- File upload handling

Example:
    Basic usage example:

    >>> from api.main import create_app
    >>> app = create_app()
    >>> # Use with uvicorn: uvicorn api.main:app --reload
"""

__version__ = "0.1.0"
__author__ = "Benchmark Analyzer Team"
__email__ = "benchmark-analyzer@company.com"
__license__ = "MIT"
__description__ = "REST API for Benchmark Analyzer framework"
__url__ = "https://github.com/company/benchmark-analyzer"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "__url__",
    "get_version",
    "get_api_info",
]


def get_version() -> str:
    """Get API version."""
    return __version__


def get_api_info() -> dict:
    """Get API information."""
    return {
        "name": "benchmark-analyzer-api",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "description": __description__,
        "url": __url__,
        "framework": "FastAPI",
    }


# Import main components for convenience
try:
    from .main import Application, create_app
    from .config.settings import config

    # Add to __all__ if imports are successful
    __all__.extend([
        "Application",
        "create_app",
        "config",
    ])

except ImportError as e:
    # Handle import errors gracefully during package installation
    import warnings
    warnings.warn(f"Some API components could not be imported: {e}")


# Set up logging for the API package
import logging

# Create a logger for the API package
logger = logging.getLogger(__name__)

# Add a null handler to prevent logging errors if no handler is configured
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


# API status information
def get_status() -> dict:
    """Get API status information."""
    try:
        from .config.settings import config
        return {
            "status": "available",
            "version": __version__,
            "environment": config.get("environment", {}).get("name", "unknown"),
            "debug": config.get("app", {}).get("debug", False),
        }
    except Exception as e:
        return {
            "status": "error",
            "version": __version__,
            "error": str(e),
        }
