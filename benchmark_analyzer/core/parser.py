"""Parser system for benchmark analyzer test results."""

import csv
import json
import logging
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml

from ..config import Config, get_config

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Exception raised when parsing fails."""
    pass


class BaseParser(ABC):
    """Abstract base class for test result parsers."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize parser."""
        self.config = config or get_config()

    @abstractmethod
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single result file."""
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        pass

    @abstractmethod
    def get_test_type(self) -> str:
        """Get the test type this parser handles."""
        pass

    def parse_package(self, package_path: Path) -> List[Dict[str, Any]]:
        """Parse a ZIP package containing test results."""
        try:
            results = []

            if package_path.suffix.lower() == '.zip':
                # Extract and parse ZIP file
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    # Create temporary directory for extraction
                    temp_dir = self.config.paths.temp_dir / f"extract_{package_path.stem}"
                    temp_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        # Extract all files
                        zip_ref.extractall(temp_dir)

                        # Parse each valid file
                        for extracted_file in temp_dir.rglob('*'):
                            if extracted_file.is_file() and self._is_valid_result_file(extracted_file):
                                try:
                                    result = self.parse_file(extracted_file)
                                    if result:
                                        results.append(result)
                                except Exception as e:
                                    logger.warning(f"Failed to parse {extracted_file}: {e}")

                    finally:
                        # Clean up temporary directory
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)

            else:
                # Parse single file
                if self._is_valid_result_file(package_path):
                    result = self.parse_file(package_path)
                    if result:
                        results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to parse package {package_path}: {e}")
            raise ParseError(f"Failed to parse package: {e}")

    def _is_valid_result_file(self, file_path: Path) -> bool:
        """Check if file is a valid result file for this parser."""
        return file_path.suffix.lower() in self.get_supported_extensions()

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate the structure of parsed result."""
        # Basic validation - subclasses can override
        return isinstance(result, dict) and len(result) > 0

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize result to standard format."""
        # Default implementation - subclasses can override
        return result

    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information."""
        return {
            'test_type': self.get_test_type(),
            'supported_extensions': self.get_supported_extensions(),
            'class_name': self.__class__.__name__
        }


class JSONParser(BaseParser):
    """Parser for JSON format test results."""

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ParseError(f"JSON file must contain an object, got {type(data)}")

            return self.normalize_result(data)

        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ParseError(f"Failed to parse JSON file {file_path}: {e}")

    def get_supported_extensions(self) -> List[str]:
        """Get supported extensions."""
        return ['.json']


class CSVParser(BaseParser):
    """Parser for CSV format test results."""

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse CSV file."""
        try:
            results = []

            with open(file_path, 'r', newline='') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert string values to appropriate types
                    normalized_row = self._convert_csv_row(row)
                    results.append(normalized_row)

            # If single row, return as dict; multiple rows as list
            if len(results) == 1:
                return self.normalize_result(results[0])
            else:
                return self.normalize_result({'results': results})

        except Exception as e:
            raise ParseError(f"Failed to parse CSV file {file_path}: {e}")

    def _convert_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Convert CSV row strings to appropriate types."""
        converted = {}

        for key, value in row.items():
            if not value:  # Empty string
                converted[key] = None
                continue

            # Try to convert to number
            try:
                # Try integer first
                if '.' not in value:
                    converted[key] = int(value)
                else:
                    converted[key] = float(value)
            except ValueError:
                # Try boolean
                if value.lower() in ('true', 'false'):
                    converted[key] = value.lower() == 'true'
                else:
                    # Keep as string
                    converted[key] = value

        return converted

    def get_supported_extensions(self) -> List[str]:
        """Get supported extensions."""
        return ['.csv']


class MemoryBandwidthParser(CSVParser):
    """Parser for memory bandwidth test results."""

    def get_test_type(self) -> str:
        """Get test type."""
        return "memory_bandwidth"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize memory bandwidth result."""
        # Add timestamp if not present
        if 'timestamp' not in result:
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()

        # Ensure required fields exist
        required_fields = ['test_name', 'read_bw', 'write_bw']
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field '{field}' in memory bandwidth result")

        return result

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate memory bandwidth result structure."""
        required_fields = ['test_name', 'read_bw', 'write_bw']
        return all(field in result for field in required_fields)


class CpuLatencyParser(JSONParser):
    """Parser for CPU latency test results."""

    def get_test_type(self) -> str:
        """Get test type."""
        return "cpu_latency"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CPU latency result."""
        # Add timestamp if not present
        if 'timestamp' not in result:
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()

        # Calculate average if not present but latencies are available
        if 'average_ns' not in result and 'latencies_ns' in result:
            latencies = result['latencies_ns']
            if isinstance(latencies, list) and latencies:
                result['average_ns'] = sum(latencies) / len(latencies)

        return result

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate CPU latency result structure."""
        required_fields = ['test_name', 'latencies_ns', 'average_ns']
        return all(field in result for field in required_fields)


class CpuMemParser(JSONParser):
    """Parser for CPU and Memory benchmark results."""

    def get_test_type(self) -> str:
        """Get test type."""
        return "cpu_mem"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CPU/Memory result."""
        # Add timestamp if not present
        if 'timestamp' not in result:
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()

        return result

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate CPU/Memory result structure."""
        # Check for at least one CPU or memory metric
        cpu_metrics = [
            'sysbench_cpu_events_per_second',
            'sysbench_cpu_duration_sec'
        ]

        memory_metrics = [
            'memory_idle_latency_ns',
            'memory_peak_injection_bandwidth_mbs',
            'sysbench_ram_memory_bandwidth_mibs'
        ]

        has_cpu = any(metric in result for metric in cpu_metrics)
        has_memory = any(metric in result for metric in memory_metrics)

        return has_cpu or has_memory


class ParserRegistry:
    """Registry for managing test result parsers."""

    _parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, test_type: str, parser_class: Type[BaseParser]) -> None:
        """Register a parser for a test type."""
        cls._parsers[test_type] = parser_class
        logger.debug(f"Registered parser {parser_class.__name__} for test type '{test_type}'")

    @classmethod
    def get_parser(cls, test_type: str, config: Optional[Config] = None) -> BaseParser:
        """Get parser instance for test type."""
        if test_type not in cls._parsers:
            raise ValueError(f"No parser registered for test type: {test_type}")

        parser_class = cls._parsers[test_type]
        return parser_class(config)

    @classmethod
    def get_available_test_types(cls) -> List[str]:
        """Get list of available test types."""
        return sorted(cls._parsers.keys())

    @classmethod
    def is_test_type_supported(cls, test_type: str) -> bool:
        """Check if test type is supported."""
        return test_type in cls._parsers

    @classmethod
    def get_parser_info(cls, test_type: str) -> Dict[str, Any]:
        """Get parser information for test type."""
        if test_type not in cls._parsers:
            raise ValueError(f"No parser registered for test type: {test_type}")

        parser_class = cls._parsers[test_type]
        # Create temporary instance to get info
        temp_parser = parser_class()
        return temp_parser.get_parser_info()

    @classmethod
    def get_all_parser_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information for all registered parsers."""
        info = {}
        for test_type in cls._parsers:
            try:
                info[test_type] = cls.get_parser_info(test_type)
            except Exception as e:
                logger.error(f"Failed to get info for parser {test_type}: {e}")
                info[test_type] = {"error": str(e)}
        return info

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered parsers."""
        cls._parsers.clear()
        logger.debug("Parser registry cleared")


# Register default parsers
ParserRegistry.register("memory_bandwidth", MemoryBandwidthParser)
ParserRegistry.register("cpu_latency", CpuLatencyParser)
ParserRegistry.register("cpu_mem", CpuMemParser)


class ParserFactory:
    """Factory for creating parsers."""

    @staticmethod
    def create_parser(test_type: str, config: Optional[Config] = None) -> BaseParser:
        """Create parser for test type."""
        return ParserRegistry.get_parser(test_type, config)

    @staticmethod
    def auto_detect_parser(file_path: Path) -> Optional[BaseParser]:
        """Auto-detect parser based on file content or name."""
        # Try to detect based on file name patterns
        file_name = file_path.name.lower()

        if 'memory' in file_name or 'bandwidth' in file_name:
            return ParserRegistry.get_parser("memory_bandwidth")
        elif 'cpu' in file_name or 'latency' in file_name:
            return ParserRegistry.get_parser("cpu_latency")
        elif 'sysbench' in file_name:
            return ParserRegistry.get_parser("cpu_mem")

        # Try to detect based on file extension
        extension = file_path.suffix.lower()
        if extension == '.json':
            # Default to CPU latency for JSON files
            return ParserRegistry.get_parser("cpu_latency")
        elif extension == '.csv':
            # Default to memory bandwidth for CSV files
            return ParserRegistry.get_parser("memory_bandwidth")

        return None

    @staticmethod
    def get_available_parsers() -> List[str]:
        """Get list of available parsers."""
        return ParserRegistry.get_available_test_types()
