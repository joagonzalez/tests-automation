"""Validation service for API operations."""

import logging
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

import yaml
from jsonschema import Draft7Validator, ValidationError
from sqlalchemy.orm import Session

from benchmark_analyzer.core.validator import SchemaValidator, ValidationResult
from benchmark_analyzer.db.models import TestType, Environment, TestRun
from api.config.settings import config

logger = logging.getLogger(__name__)


class APIValidationError(Exception):
    """Custom validation error for API operations."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []


class ValidationService:
    """Service for validating API requests and data."""

    def __init__(self):
        """Initialize validation service."""
        self.schema_validator = SchemaValidator()
        self._load_validation_rules()

    def _load_validation_rules(self):
        """Load validation rules and constraints."""
        self.validation_rules = {
            "test_type": {
                "name": {
                    "min_length": 1,
                    "max_length": 64,
                    "pattern": r"^[a-zA-Z0-9_-]+$",
                    "reserved_names": ["admin", "system", "test", "default"]
                },
                "description": {
                    "max_length": 500
                }
            },
            "environment": {
                "name": {
                    "max_length": 128
                },
                "type": {
                    "max_length": 32,
                    "allowed_values": ["lab", "cloud", "virtual", "bare-metal", "container"]
                },
                "comments": {
                    "max_length": 1000
                }
            },
            "test_run": {
                "engineer": {
                    "max_length": 64
                },
                "comments": {
                    "max_length": 1000
                }
            },
            "upload": {
                "max_file_size": 100 * 1024 * 1024,  # 100MB
                "allowed_extensions": {
                    "test_results": [".zip"],
                    "environment": [".yaml", ".yml"],
                    "schema": [".json"],
                    "bom": [".yaml", ".yml"]
                }
            }
        }

    def validate_test_type_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate test type data."""
        errors = []

        # Validate name
        if "name" in data:
            name = data["name"]
            if not isinstance(name, str):
                errors.append("Test type name must be a string")
            else:
                rules = self.validation_rules["test_type"]["name"]

                if len(name) < rules["min_length"]:
                    errors.append(f"Test type name must be at least {rules['min_length']} characters")

                if len(name) > rules["max_length"]:
                    errors.append(f"Test type name must be at most {rules['max_length']} characters")

                import re
                if not re.match(rules["pattern"], name):
                    errors.append("Test type name can only contain letters, numbers, hyphens, and underscores")

                if name.lower() in rules["reserved_names"]:
                    errors.append(f"Test type name '{name}' is reserved")

        # Validate description
        if "description" in data and data["description"] is not None:
            description = data["description"]
            if not isinstance(description, str):
                errors.append("Test type description must be a string")
            else:
                max_length = self.validation_rules["test_type"]["description"]["max_length"]
                if len(description) > max_length:
                    errors.append(f"Test type description must be at most {max_length} characters")

        return ValidationResult(len(errors) == 0, errors)

    def validate_environment_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate environment data."""
        errors = []

        # Validate name
        if "name" in data and data["name"] is not None:
            name = data["name"]
            if not isinstance(name, str):
                errors.append("Environment name must be a string")
            else:
                max_length = self.validation_rules["environment"]["name"]["max_length"]
                if len(name) > max_length:
                    errors.append(f"Environment name must be at most {max_length} characters")

        # Validate type
        if "type" in data and data["type"] is not None:
            env_type = data["type"]
            if not isinstance(env_type, str):
                errors.append("Environment type must be a string")
            else:
                rules = self.validation_rules["environment"]["type"]
                if len(env_type) > rules["max_length"]:
                    errors.append(f"Environment type must be at most {rules['max_length']} characters")

                if env_type not in rules["allowed_values"]:
                    errors.append(f"Environment type must be one of: {', '.join(rules['allowed_values'])}")

        # Validate comments
        if "comments" in data and data["comments"] is not None:
            comments = data["comments"]
            if not isinstance(comments, str):
                errors.append("Environment comments must be a string")
            else:
                max_length = self.validation_rules["environment"]["comments"]["max_length"]
                if len(comments) > max_length:
                    errors.append(f"Environment comments must be at most {max_length} characters")

        # Validate tools
        if "tools" in data and data["tools"] is not None:
            tools = data["tools"]
            if not isinstance(tools, dict):
                errors.append("Environment tools must be a JSON object")
            else:
                # Validate tools structure
                tool_errors = self._validate_tools_structure(tools)
                errors.extend(tool_errors)

        # Validate metadata
        if "metadata" in data and data["metadata"] is not None:
            metadata = data["metadata"]
            if not isinstance(metadata, dict):
                errors.append("Environment metadata must be a JSON object")

        return ValidationResult(len(errors) == 0, errors)

    def _validate_tools_structure(self, tools: Dict[str, Any]) -> List[str]:
        """Validate tools structure."""
        errors = []

        # Common tool validation
        for tool_name, tool_config in tools.items():
            if not isinstance(tool_name, str):
                errors.append("Tool names must be strings")
                continue

            if not isinstance(tool_config, dict):
                errors.append(f"Tool '{tool_name}' configuration must be a JSON object")
                continue

            # Validate common tool properties
            if "version" in tool_config:
                if not isinstance(tool_config["version"], str):
                    errors.append(f"Tool '{tool_name}' version must be a string")

            if "command" in tool_config:
                if not isinstance(tool_config["command"], str):
                    errors.append(f"Tool '{tool_name}' command must be a string")

            if "options" in tool_config:
                if not isinstance(tool_config["options"], (dict, list)):
                    errors.append(f"Tool '{tool_name}' options must be a JSON object or array")

        return errors

    def validate_test_run_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate test run data."""
        errors = []

        # Validate required fields
        if "test_type_id" not in data:
            errors.append("Test type ID is required")
        elif not isinstance(data["test_type_id"], str):
            errors.append("Test type ID must be a string")

        # Validate optional fields
        if "engineer" in data and data["engineer"] is not None:
            engineer = data["engineer"]
            if not isinstance(engineer, str):
                errors.append("Engineer must be a string")
            else:
                max_length = self.validation_rules["test_run"]["engineer"]["max_length"]
                if len(engineer) > max_length:
                    errors.append(f"Engineer name must be at most {max_length} characters")

        if "comments" in data and data["comments"] is not None:
            comments = data["comments"]
            if not isinstance(comments, str):
                errors.append("Comments must be a string")
            else:
                max_length = self.validation_rules["test_run"]["comments"]["max_length"]
                if len(comments) > max_length:
                    errors.append(f"Comments must be at most {max_length} characters")

        if "configuration" in data and data["configuration"] is not None:
            configuration = data["configuration"]
            if not isinstance(configuration, dict):
                errors.append("Configuration must be a JSON object")

        return ValidationResult(len(errors) == 0, errors)

    def validate_file_upload(self, filename: str, file_size: int, file_type: str) -> ValidationResult:
        """Validate file upload."""
        errors = []

        # Validate file size
        max_size = self.validation_rules["upload"]["max_file_size"]
        if file_size > max_size:
            errors.append(f"File size {file_size} bytes exceeds maximum allowed size of {max_size} bytes")

        # Validate file extension
        if file_type not in self.validation_rules["upload"]["allowed_extensions"]:
            errors.append(f"Invalid file type: {file_type}")
        else:
            allowed_extensions = self.validation_rules["upload"]["allowed_extensions"][file_type]
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                errors.append(f"File extension {file_ext} not allowed for {file_type}. Allowed: {allowed_extensions}")

        # Validate filename
        if not filename or len(filename.strip()) == 0:
            errors.append("Filename cannot be empty")

        # Check for potentially dangerous filenames
        dangerous_patterns = ["../", "..\\", "/etc/", "c:\\", ".exe", ".bat", ".sh"]
        filename_lower = filename.lower()
        for pattern in dangerous_patterns:
            if pattern in filename_lower:
                errors.append(f"Filename contains potentially dangerous pattern: {pattern}")
                break

        return ValidationResult(len(errors) == 0, errors)

    def validate_json_schema(self, schema_data: Dict[str, Any]) -> ValidationResult:
        """Validate JSON schema."""
        errors = []

        try:
            # Validate the schema itself
            Draft7Validator.check_schema(schema_data)
        except Exception as e:
            errors.append(f"Invalid JSON schema: {str(e)}")

        # Additional schema validation rules
        if "type" not in schema_data:
            errors.append("Schema must have a 'type' property")

        if "properties" not in schema_data and schema_data.get("type") == "object":
            errors.append("Object schema should have a 'properties' property")

        return ValidationResult(len(errors) == 0, errors)

    def validate_yaml_data(self, yaml_content: str) -> Tuple[ValidationResult, Optional[Dict[str, Any]]]:
        """Validate YAML data."""
        errors = []
        data = None

        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML: {str(e)}")

        if data is not None and not isinstance(data, dict):
            errors.append("YAML must contain a dictionary/object at root level")

        return ValidationResult(len(errors) == 0, errors), data

    def validate_data_against_schema(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Validate data against JSON schema."""
        try:
            validator = Draft7Validator(schema)
            errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

            if errors:
                error_messages = []
                for error in errors:
                    path = ".".join(str(p) for p in error.path) if error.path else "root"
                    error_messages.append(f"Path '{path}': {error.message}")

                return ValidationResult(False, error_messages)

            return ValidationResult(True, [])

        except Exception as e:
            return ValidationResult(False, [f"Schema validation failed: {str(e)}"])

    def validate_business_rules(self, session: Session, operation: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate business rules."""
        errors = []

        if operation == "create_test_type":
            # Check if test type name already exists
            if "name" in data:
                existing = session.query(TestType).filter(TestType.name == data["name"]).first()
                if existing:
                    errors.append(f"Test type with name '{data['name']}' already exists")

        elif operation == "update_test_type":
            # Check if new name conflicts with existing test type
            if "name" in data and "test_type_id" in data:
                existing = session.query(TestType).filter(
                    TestType.name == data["name"],
                    TestType.test_type_id != data["test_type_id"]
                ).first()
                if existing:
                    errors.append(f"Test type with name '{data['name']}' already exists")

        elif operation == "delete_test_type":
            # Check if test type has associated test runs
            if "test_type_id" in data:
                test_type = session.query(TestType).filter(TestType.test_type_id == data["test_type_id"]).first()
                if test_type and test_type.test_runs:
                    errors.append(f"Cannot delete test type '{test_type.name}' because it has {len(test_type.test_runs)} associated test runs")

        elif operation == "delete_environment":
            # Check if environment has associated test runs
            if "environment_id" in data:
                environment = session.query(Environment).filter(Environment.id == data["environment_id"]).first()
                if environment and environment.test_runs:
                    errors.append(f"Cannot delete environment '{environment.name}' because it has {len(environment.test_runs)} associated test runs")

        elif operation == "create_test_run":
            # Validate test type exists
            if "test_type_id" in data:
                test_type = session.query(TestType).filter(TestType.test_type_id == data["test_type_id"]).first()
                if not test_type:
                    errors.append(f"Test type with ID '{data['test_type_id']}' not found")

            # Validate environment exists if provided
            if "environment_id" in data and data["environment_id"]:
                environment = session.query(Environment).filter(Environment.id == data["environment_id"]).first()
                if not environment:
                    errors.append(f"Environment with ID '{data['environment_id']}' not found")

        return ValidationResult(len(errors) == 0, errors)

    def validate_metric_values(self, metrics: Dict[str, Any]) -> ValidationResult:
        """Validate metric values."""
        errors = []

        # Define metric validation rules
        metric_rules = {
            "memory_idle_latency_ns": {"type": "float", "min": 0, "max": 1e9},
            "memory_peak_injection_bandwidth_mbs": {"type": "float", "min": 0, "max": 100000},
            "ramspeed_smp_bandwidth_mbs_add": {"type": "float", "min": 0, "max": 100000},
            "ramspeed_smp_bandwidth_mbs_copy": {"type": "float", "min": 0, "max": 100000},
            "sysbench_ram_memory_bandwidth_mibs": {"type": "int", "min": 0, "max": 100000},
            "sysbench_ram_memory_test_duration_sec": {"type": "int", "min": 0, "max": 86400},
            "sysbench_ram_memory_test_mode": {"type": "str", "allowed": ["read", "write", "random"]},
            "sysbench_cpu_events_per_second": {"type": "int", "min": 0, "max": 1000000},
            "sysbench_cpu_duration_sec": {"type": "int", "min": 0, "max": 86400},
            "sysbench_cpu_test_mode": {"type": "str", "allowed": ["cpu", "threads", "events"]},
        }

        for metric_name, value in metrics.items():
            if metric_name not in metric_rules:
                errors.append(f"Unknown metric: {metric_name}")
                continue

            if value is None:
                continue  # Allow null values

            rule = metric_rules[metric_name]

            # Type validation
            if rule["type"] == "float":
                if not isinstance(value, (int, float)):
                    errors.append(f"Metric '{metric_name}' must be a number")
                    continue
                value = float(value)
            elif rule["type"] == "int":
                if not isinstance(value, int):
                    errors.append(f"Metric '{metric_name}' must be an integer")
                    continue
            elif rule["type"] == "str":
                if not isinstance(value, str):
                    errors.append(f"Metric '{metric_name}' must be a string")
                    continue

            # Range validation
            if "min" in rule and value < rule["min"]:
                errors.append(f"Metric '{metric_name}' must be >= {rule['min']}")

            if "max" in rule and value > rule["max"]:
                errors.append(f"Metric '{metric_name}' must be <= {rule['max']}")

            # Allowed values validation
            if "allowed" in rule and value not in rule["allowed"]:
                errors.append(f"Metric '{metric_name}' must be one of: {', '.join(rule['allowed'])}")

        return ValidationResult(len(errors) == 0, errors)

    def validate_query_parameters(self, params: Dict[str, Any], allowed_params: List[str]) -> ValidationResult:
        """Validate query parameters."""
        errors = []

        # Check for unknown parameters
        for param in params:
            if param not in allowed_params:
                errors.append(f"Unknown query parameter: {param}")

        # Validate common parameters
        if "page" in params:
            try:
                page = int(params["page"])
                if page < 1:
                    errors.append("Page number must be >= 1")
            except (ValueError, TypeError):
                errors.append("Page number must be an integer")

        if "page_size" in params:
            try:
                page_size = int(params["page_size"])
                if page_size < 1:
                    errors.append("Page size must be >= 1")
                elif page_size > 1000:
                    errors.append("Page size must be <= 1000")
            except (ValueError, TypeError):
                errors.append("Page size must be an integer")

        if "sort_order" in params:
            if params["sort_order"] not in ["asc", "desc"]:
                errors.append("Sort order must be 'asc' or 'desc'")

        # Validate date parameters
        date_params = ["date_from", "date_to"]
        for param in date_params:
            if param in params and params[param]:
                try:
                    datetime.strptime(params[param], "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Parameter '{param}' must be in YYYY-MM-DD format")

        return ValidationResult(len(errors) == 0, errors)


# Global validation service instance
validation_service = ValidationService()
