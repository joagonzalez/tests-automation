"""Test configuration and utilities for benchmark analyzer."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    "database": {
        "host": "localhost",
        "port": 3306,
        "username": "test_user",
        "password": "test_password",
        "database": "test_perf_framework",
        "driver": "pymysql",
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8001,
        "debug": True,
        "testing": True,
    },
    "paths": {
        "temp_dir": tempfile.mkdtemp(),
        "test_data_dir": Path(__file__).parent / "test_data",
        "fixtures_dir": Path(__file__).parent / "fixtures",
    },
    "logging": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}

# Test markers
TEST_MARKERS = {
    "unit": "Unit tests",
    "integration": "Integration tests",
    "slow": "Slow tests",
    "database": "Tests requiring database",
    "api": "API tests",
    "parser": "Parser tests",
    "validator": "Validator tests",
}

# Mock data for tests
MOCK_TEST_RESULT = {
    "test_name": "test_cpu_mem_001",
    "timestamp": "2024-01-15T14:30:00Z",
    "test_duration_sec": 300,
    "memory_idle_latency_ns": 120.5,
    "memory_peak_injection_bandwidth_mbs": 25600.0,
    "sysbench_cpu_events_per_second": 15000,
    "sysbench_cpu_duration_sec": 60,
    "sysbench_cpu_test_mode": "cpu",
    "cpu_utilization_percent": 95.2,
    "memory_utilization_percent": 45.8,
    "cpu_cores": 8,
    "memory_total_mb": 32768,
    "threads_used": 8,
}

MOCK_ENVIRONMENT = {
    "name": "test_environment",
    "type": "testing",
    "comments": "Test environment for unit tests",
    "tools": {
        "python": "3.11.7",
        "sysbench": "1.0.20",
    },
    "metadata": {
        "location": "test-lab",
        "hardware": {
            "cpu_model": "Test CPU",
            "cpu_cores": 8,
            "memory_total": "32GB",
        },
    },
}

MOCK_BOM = {
    "hardware": {
        "name": "test-hardware",
        "version": "1.0",
        "specs": {
            "cpu": "Test CPU 8-core",
            "ram": "32GB DDR4",
            "storage": "1TB NVMe SSD",
        },
    },
    "software": {
        "name": "test-software",
        "version": "1.0",
        "specs": {
            "os": "Ubuntu 22.04 LTS",
            "kernel": "5.15.0-test",
            "python": "3.11.7",
        },
    },
}


def get_test_config() -> Dict[str, Any]:
    """Get test configuration."""
    return TEST_CONFIG.copy()


def get_test_db_url() -> str:
    """Get test database URL."""
    db_config = TEST_CONFIG["database"]
    return (
        f"mysql+{db_config['driver']}://"
        f"{db_config['username']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/"
        f"{db_config['database']}"
    )


def get_test_data_path(filename: str) -> Path:
    """Get path to test data file."""
    return TEST_CONFIG["paths"]["test_data_dir"] / filename


def get_fixtures_path(filename: str) -> Path:
    """Get path to test fixtures file."""
    return TEST_CONFIG["paths"]["fixtures_dir"] / filename


def create_temp_file(content: str, suffix: str = ".tmp") -> Path:
    """Create a temporary file with content."""
    temp_file = Path(tempfile.mktemp(suffix=suffix))
    temp_file.write_text(content)
    return temp_file


def create_temp_json_file(data: Dict[str, Any]) -> Path:
    """Create a temporary JSON file."""
    import json
    content = json.dumps(data, indent=2)
    return create_temp_file(content, ".json")


def create_temp_yaml_file(data: Dict[str, Any]) -> Path:
    """Create a temporary YAML file."""
    import yaml
    content = yaml.dump(data, default_flow_style=False)
    return create_temp_file(content, ".yaml")


def create_temp_csv_file(data: list) -> Path:
    """Create a temporary CSV file."""
    import csv
    import io

    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return create_temp_file(output.getvalue(), ".csv")


class TestDatabase:
    """Test database utilities."""

    @staticmethod
    def create_test_db():
        """Create test database."""
        # This would be implemented to create a test database
        pass

    @staticmethod
    def drop_test_db():
        """Drop test database."""
        # This would be implemented to drop the test database
        pass

    @staticmethod
    def clean_test_db():
        """Clean test database."""
        # This would be implemented to clean the test database
        pass


class TestAPI:
    """Test API utilities."""

    @staticmethod
    def create_test_client():
        """Create test API client."""
        # This would be implemented to create a test FastAPI client
        pass


# Test environment setup
def setup_test_environment():
    """Set up test environment."""
    # Ensure test directories exist
    for path in TEST_CONFIG["paths"].values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["DB_NAME"] = TEST_CONFIG["database"]["database"]
    os.environ["API_PORT"] = str(TEST_CONFIG["api"]["port"])
    os.environ["DEBUG"] = "true"


def teardown_test_environment():
    """Tear down test environment."""
    # Clean up temporary files
    import shutil
    temp_dir = TEST_CONFIG["paths"]["temp_dir"]
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


# Initialize test environment when module is imported
setup_test_environment()
