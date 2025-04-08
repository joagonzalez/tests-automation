from abc import ABC, abstractmethod
from pathlib import Path
import csv
import json
import yaml
from typing import Dict, Any, Type
import zipfile
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Abstract base class for test result parsers."""

    @abstractmethod
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single result file."""
        pass

    def parse_package(self, package_path: Path) -> Dict[str, Any]:
        """Extract and parse files from a zip package."""
        # Create a temporary directory using tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.debug(f"Extracting zip to temporary directory: {temp_dir}")
                with zipfile.ZipFile(package_path) as zf:
                    zf.extractall(temp_dir)

                # Find and parse relevant files
                results = []
                temp_path = Path(temp_dir)
                for file_path in temp_path.rglob("*"):  # Use rglob for recursive search
                    if file_path.is_file() and self._is_valid_result_file(file_path):
                        logger.debug(f"Parsing file: {file_path}")
                        results.append(self.parse_file(file_path))

                logger.debug(f"Found {len(results)} valid result files")
                return {"results": results}

            except Exception as e:
                logger.error(f"Error processing zip package: {str(e)}")
                raise
            
    @abstractmethod
    def _is_valid_result_file(self, file_path: Path) -> bool:
        """Check if a file is valid for this parser."""
        pass

class MemoryBandwidthParser(BaseParser):
    """Parser for memory bandwidth test results."""

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path) as f:
            reader = csv.DictReader(f)
            data = next(reader)  # Assuming single row for this example
            return {
                "test_name": data["test_name"],
                "read_bw": float(data["read_bw"]),
                "write_bw": float(data["write_bw"]),
                "timestamp": data["timestamp"]
            }

    def _is_valid_result_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".csv"

class CpuLatencyParser(BaseParser):
    """Parser for CPU latency test results."""

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path) as f:
            data = json.load(f)
            return {
                "test_name": data["test_name"],
                "latencies_ns": data["latencies_ns"],
                "average_ns": data["average_ns"],
                "timestamp": data["timestamp"]
            }

    def _is_valid_result_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".json"

class ParserRegistry:
    """Registry for test type parsers."""

    _parsers: Dict[str, Type[BaseParser]] = {
        "memory_bandwidth": MemoryBandwidthParser,
        "cpu_latency": CpuLatencyParser
    }

    @classmethod
    def get_parser(cls, test_type: str) -> BaseParser:
        """Get parser instance for a test type."""
        if test_type not in cls._parsers:
            raise ValueError(f"Unknown test type: {test_type}")
        return cls._parsers[test_type]()

    @classmethod
    def get_available_test_types(cls) -> list[str]:
        """Get list of registered test types."""
        return list(cls._parsers.keys())