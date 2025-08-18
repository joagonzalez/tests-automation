"""
Benchmark Analyzer - A framework for analyzing hardware/software benchmark results.

This package provides tools for importing, processing, and analyzing benchmark test results
from various hardware and software environments. It includes:

- CLI tools for importing and querying test results
- Database models for storing benchmark data
- Parsers for different test result formats
- Validation schemas for test results
- Configuration management
- API for accessing stored results

Example:
    Basic usage example:

    >>> from benchmark_analyzer.config import get_config
    >>> from benchmark_analyzer.core.parser import ParserRegistry
    >>> config = get_config()
    >>> parser = ParserRegistry.get_parser("cpu_mem")
"""

__version__ = "0.1.0"
__author__ = "Benchmark Analyzer Team"
__email__ = "benchmark-analyzer@TBD"
__license__ = "TBD"
__description__ = "Framework for analyzing hardware/software benchmark results"
__url__ = "https://repo_url/benchmark-analyzer"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "__url__",
    "get_version",
    "get_package_info",
]


def get_version() -> str:
    """Get package version."""
    return __version__


def get_package_info() -> dict:
    """Get package information."""
    return {
        "name": "benchmark-analyzer",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "description": __description__,
        "url": __url__,
    }


# Import main components for convenience
try:
    from .config import Config, get_config
    from .core.parser import ParserRegistry
    from .core.validator import SchemaValidator
    from .core.loader import DataLoader
    from .db.connector import DatabaseManager, get_db_manager

    # Add to __all__ if imports are successful
    __all__.extend([
        "Config",
        "get_config",
        "ParserRegistry",
        "SchemaValidator",
        "DataLoader",
        "DatabaseManager",
        "get_db_manager",
    ])

except ImportError as e:
    # Handle import errors gracefully during package installation
    import warnings
    warnings.warn(f"Some components could not be imported: {e}")


# Set up logging
import logging

# Create a logger for the package
logger = logging.getLogger(__name__)

# Add a null handler to prevent logging errors if no handler is configured
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
