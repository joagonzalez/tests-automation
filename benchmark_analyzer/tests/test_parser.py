# tests/test_parser.py
import pytest
from pathlib import Path
import json
import csv
from benchmark_analyzer.core.parser import MemoryBandwidthParser, CpuLatencyParser

@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test files with sample data."""
    # Create memory bandwidth CSV
    memory_csv = tmp_path / "test_memory.csv"
    with open(memory_csv, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["test_name", "read_bw", "write_bw", "timestamp"])
        writer.writerow(["memtest1", "2300", "2100", "2024-03-01T15:23:00"])

    # Create CPU latency JSON
    cpu_json = tmp_path / "test_cpu.json"
    cpu_data = {
        "test_name": "latency_test",
        "latencies_ns": [102, 110, 98, 107],
        "average_ns": 104.25,
        "timestamp": "2024-03-01T16:00:00"
    }
    with open(cpu_json, "w") as f:
        json.dump(cpu_data, f)

    return {"memory": memory_csv, "cpu": cpu_json}

def test_memory_bandwidth_parser(temp_test_files):
    """Test memory bandwidth parser with CSV input."""
    parser = MemoryBandwidthParser()
    result = parser.parse_file(temp_test_files["memory"])

    assert isinstance(result, dict)
    assert result["test_name"] == "memtest1"
    assert result["read_bw"] == 2300.0
    assert result["write_bw"] == 2100.0
    assert result["timestamp"] == "2024-03-01T15:23:00"

def test_cpu_latency_parser(temp_test_files):
    """Test CPU latency parser with JSON input."""
    parser = CpuLatencyParser()
    result = parser.parse_file(temp_test_files["cpu"])

    assert isinstance(result, dict)
    assert result["test_name"] == "latency_test"
    assert result["average_ns"] == 104.25
    assert len(result["latencies_ns"]) == 4
    assert result["timestamp"] == "2024-03-01T16:00:00"

def test_memory_bandwidth_parser_invalid_file(tmp_path):
    """Test parser with invalid CSV file."""
    invalid_file = tmp_path / "invalid.csv"
    # Create an invalid CSV file (missing required columns)
    with open(invalid_file, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["test_name", "invalid_column"])  # Missing required columns
        writer.writerow(["test1", "value1"])

    parser = MemoryBandwidthParser()
    with pytest.raises(KeyError) as exc_info:
        parser.parse_file(invalid_file)

def test_cpu_latency_parser_invalid_file(tmp_path):
    """Test parser with invalid JSON file."""
    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w") as f:
        f.write("{invalid json}")  # Invalid JSON syntax

    parser = CpuLatencyParser()
    with pytest.raises(json.JSONDecodeError):
        parser.parse_file(invalid_file)

def test_parser_file_type_validation():
    """Test parser file type validation."""
    parser_memory = MemoryBandwidthParser()
    parser_cpu = CpuLatencyParser()

    assert parser_memory._is_valid_result_file(Path("test.csv")) is True
    assert parser_memory._is_valid_result_file(Path("test.json")) is False
    assert parser_cpu._is_valid_result_file(Path("test.json")) is True
    assert parser_cpu._is_valid_result_file(Path("test.csv")) is False

def test_package_parsing(tmp_path):
    """Test parsing of a ZIP package."""
    # Create test files
    test_dir = tmp_path / "test_package"
    test_dir.mkdir()
    
    # Create memory bandwidth test file
    memory_file = test_dir / "memory_test.csv"
    with open(memory_file, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["test_name", "read_bw", "write_bw", "timestamp"])
        writer.writerow(["memtest1", "2300", "2100", "2024-03-01T15:23:00"])

    # Create ZIP file
    import zipfile
    zip_path = tmp_path / "test_results.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(memory_file, memory_file.name)

    # Test package parsing
    parser = MemoryBandwidthParser()
    result = parser.parse_package(zip_path)

    assert isinstance(result, dict)
    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["test_name"] == "memtest1"
    assert result["results"][0]["read_bw"] == 2300.0