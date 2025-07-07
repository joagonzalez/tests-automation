"""Pytest configuration and shared fixtures."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmark_analyzer.db.models import Base
from benchmark_analyzer.db.connector import DatabaseManager
from benchmark_analyzer.config import Config, get_config
from api.main import create_app
from api.config.settings import config as api_config


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Test configuration."""
    return {
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False,
            "pool_pre_ping": True,
        },
        "api": {
            "testing": True,
            "debug": True,
        },
        "upload": {
            "directory": "/tmp/test_uploads",
            "temp_directory": "/tmp/test_temp",
            "max_file_size": 10 * 1024 * 1024,  # 10MB for testing
        },
        "logging": {
            "level": "DEBUG",
            "file_logging": False,
        }
    }


@pytest.fixture(scope="session")
def test_engine(test_config):
    """Create test database engine."""
    engine = create_engine(
        test_config["database"]["url"],
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=test_config["database"]["echo"],
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create test session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_session_factory) -> Generator[Session, None, None]:
    """Create test database session."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_db_manager(test_engine, test_session_factory):
    """Create test database manager."""
    with patch('benchmark_analyzer.db.connector.get_db_manager') as mock_get_db:
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_db_manager.engine = test_engine
        mock_db_manager.session_factory = test_session_factory
        mock_db_manager.get_session.return_value.__enter__ = lambda x: test_session_factory()
        mock_db_manager.get_session.return_value.__exit__ = lambda x, *args: None
        mock_db_manager.test_connection.return_value = True
        mock_db_manager.initialize_tables.return_value = True

        mock_get_db.return_value = mock_db_manager
        yield mock_db_manager


@pytest.fixture
def test_api_config(test_config):
    """Test API configuration."""
    test_api_config = api_config.copy()
    test_api_config.update({
        "environment": {"testing": True},
        "app": {
            **test_api_config["app"],
            "debug": True,
        },
        "database": test_config["database"],
        "upload": test_config["upload"],
    })
    return test_api_config


@pytest.fixture
def api_client(test_api_config, test_db_manager):
    """Create test API client."""
    with patch('api.config.settings.config', test_api_config):
        app = create_app(test_api_config)
        with TestClient(app) as client:
            yield client


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_uploads_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_extract_dir():
    """Create temporary extraction directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_extract_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_test_type_data():
    """Sample test type data."""
    return {
        "name": "cpu_memory_test",
        "description": "CPU and memory performance test"
    }


@pytest.fixture
def sample_environment_data():
    """Sample environment data."""
    return {
        "name": "test_lab_env",
        "type": "lab",
        "comments": "Test laboratory environment",
        "tools": {
            "sysbench": {
                "version": "1.0.20",
                "command": "sysbench",
                "options": {
                    "threads": 4,
                    "time": 60
                }
            }
        },
        "metadata": {
            "location": "Lab A",
            "contact": "test@example.com"
        }
    }


@pytest.fixture
def sample_test_run_data():
    """Sample test run data."""
    return {
        "test_type_id": "test-type-123",
        "environment_id": "env-123",
        "engineer": "Test Engineer",
        "comments": "Test run for validation",
        "configuration": {
            "test_mode": "validation",
            "duration": 60
        }
    }


@pytest.fixture
def sample_results_data():
    """Sample results data."""
    return {
        "test_run_id": "test-run-123",
        "memory_idle_latency_ns": 120.5,
        "memory_peak_injection_bandwidth_mbs": 15000.0,
        "ramspeed_smp_bandwidth_mbs_add": 12000.0,
        "ramspeed_smp_bandwidth_mbs_copy": 11000.0,
        "sysbench_ram_memory_bandwidth_mibs": 8000,
        "sysbench_ram_memory_test_duration_sec": 60,
        "sysbench_ram_memory_test_mode": "read",
        "sysbench_cpu_events_per_second": 5000,
        "sysbench_cpu_duration_sec": 60,
        "sysbench_cpu_test_mode": "cpu"
    }


@pytest.fixture
def sample_json_schema():
    """Sample JSON schema."""
    return {
        "type": "object",
        "properties": {
            "test_name": {"type": "string"},
            "duration": {"type": "integer", "minimum": 1},
            "results": {
                "type": "object",
                "properties": {
                    "cpu_score": {"type": "number"},
                    "memory_score": {"type": "number"}
                },
                "required": ["cpu_score", "memory_score"]
            }
        },
        "required": ["test_name", "duration", "results"]
    }


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content."""
    return """
name: test_environment
type: lab
comments: Test environment for validation
tools:
  sysbench:
    version: "1.0.20"
    command: sysbench
    options:
      threads: 4
      time: 60
metadata:
  location: Lab A
  contact: test@example.com
"""


@pytest.fixture
def sample_zip_file(temp_upload_dir):
    """Create sample zip file for testing."""
    import zipfile
    import json

    zip_path = temp_upload_dir / "test_results.zip"

    # Create sample data files
    sample_data = {
        "test_name": "cpu_memory_test",
        "duration": 60,
        "results": {
            "cpu_score": 1500.0,
            "memory_score": 8000.0
        }
    }

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test_data.json", json.dumps(sample_data, indent=2))
        zf.writestr("metadata.txt", "Test run metadata")

    return zip_path


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup test files after each test."""
    yield
    # Cleanup any temporary files created during tests
    test_dirs = ["/tmp/test_uploads", "/tmp/test_temp"]
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def mock_parser_registry():
    """Mock parser registry."""
    with patch('benchmark_analyzer.core.parser.ParserRegistry') as mock_registry:
        mock_registry.get_available_test_types.return_value = ["cpu_memory_test", "network_test"]
        mock_registry.get_parser_info.return_value = {
            "class_name": "TestParser",
            "description": "Test parser"
        }
        yield mock_registry


@pytest.fixture
def mock_schema_validator():
    """Mock schema validator."""
    with patch('benchmark_analyzer.core.validator.SchemaValidator') as mock_validator:
        mock_instance = Mock()
        mock_instance.validate.return_value = Mock(is_valid=True, errors=[])
        mock_instance.get_supported_test_types.return_value = ["cpu_memory_test"]
        mock_validator.return_value = mock_instance
        yield mock_validator


@pytest.fixture
def mock_data_loader():
    """Mock data loader."""
    with patch('benchmark_analyzer.core.loader.DataLoader') as mock_loader:
        mock_instance = Mock()
        mock_instance.load_test_results.return_value = True
        mock_loader.return_value = mock_instance
        yield mock_loader


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )
    config.addinivalue_line(
        "markers", "database: mark test as database test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers to tests based on file location
    for item in items:
        # Add unit marker to unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add api marker to API tests
        if "api" in str(item.fspath) or "endpoints" in str(item.fspath):
            item.add_marker(pytest.mark.api)

        # Add database marker to database tests
        if "database" in str(item.fspath) or "db" in str(item.fspath):
            item.add_marker(pytest.mark.database)


# Environment setup for tests
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Ensure test directories exist
    test_dirs = ["/tmp/test_uploads", "/tmp/test_temp"]
    for test_dir in test_dirs:
        os.makedirs(test_dir, exist_ok=True)

    yield

    # Cleanup environment
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
