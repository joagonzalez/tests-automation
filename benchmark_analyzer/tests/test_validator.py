# tests/test_validator.py
import pytest
from pathlib import Path
import json
import os
from benchmark_analyzer.core.validator import SchemaValidator

@pytest.fixture
def memory_bandwidth_schema(tmp_path, monkeypatch):
    """Create a temporary schema file for testing."""
    # Create the correct directory structure
    contracts_dir = tmp_path / "contracts"
    schema_dir = contracts_dir / "tests" / "memory_bandwidth"
    schema_dir.mkdir(parents=True)
    
    # Create the schema file
    schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "test_name": {"type": "string"},
                        "read_bw": {"type": "number"},
                        "write_bw": {"type": "number"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    },
                    "required": ["test_name", "read_bw", "write_bw", "timestamp"]
                }
            }
        },
        "required": ["results"]
    }
    
    schema_path = schema_dir / "schema.json"
    with open(schema_path, 'w') as f:
        json.dump(schema, f)

    monkeypatch.setenv("BENCHMARK_CONTRACTS_PATH", str(contracts_dir))
    return schema_path

def test_schema_validator_valid_data(memory_bandwidth_schema):
    """Test validation of valid data."""
    validator = SchemaValidator("memory_bandwidth")
    test_data = {
        "results": [{
            "test_name": "memtest1",
            "read_bw": 2300,
            "write_bw": 2100,
            "timestamp": "2024-03-01T15:23:00"
        }]
    }

    assert validator.validate(test_data) is True

def test_schema_validator_invalid_data(memory_bandwidth_schema):
    """Test validation of invalid data."""
    validator = SchemaValidator("memory_bandwidth")

    # Missing required field
    invalid_data_1 = {
        "results": [{
            "test_name": "memtest1",
            "read_bw": 2300,
            # missing write_bw
            "timestamp": "2024-03-01T15:23:00"
        }]
    }

    with pytest.raises(ValueError) as exc_info:
        validator.validate(invalid_data_1)
    assert "write_bw" in str(exc_info.value)

def test_schema_validator_empty_data(memory_bandwidth_schema):
    """Test validation of empty data."""
    validator = SchemaValidator("memory_bandwidth")

    with pytest.raises(ValueError) as exc_info:
        validator.validate({})
    assert "results" in str(exc_info.value)

def test_schema_validator_additional_properties(memory_bandwidth_schema):
    """Test validation with additional properties."""
    validator = SchemaValidator("memory_bandwidth")
    test_data = {
        "results": [{
            "test_name": "memtest1",
            "read_bw": 2300,
            "write_bw": 2100,
            "timestamp": "2024-03-01T15:23:00",
            "extra_field": "should still be valid"
        }]
    }

    assert validator.validate(test_data) is True