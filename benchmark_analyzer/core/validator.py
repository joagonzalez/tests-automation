"""Schema validator for benchmark analyzer."""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema
import yaml
from jsonschema import Draft7Validator, ValidationError

from ..config import Config, get_config

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation operation."""

    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        """Initialize validation result."""
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def __bool__(self) -> bool:
        """Return validation status."""
        return self.is_valid

    def __repr__(self) -> str:
        """String representation."""
        status = "Valid" if self.is_valid else "Invalid"
        error_count = len(self.errors)
        return f"<ValidationResult({status}, {error_count} errors)>"


class BaseValidator(ABC):
    """Base validator interface."""

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate data against schema."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get validation schema."""
        pass


class JSONSchemaValidator(BaseValidator):
    """JSON Schema validator implementation."""

    def __init__(self, schema: Dict[str, Any]):
        """Initialize with JSON schema."""
        self.schema = schema
        self.validator = Draft7Validator(schema)

    def validate(self, data: Any) -> ValidationResult:
        """Validate data against JSON schema."""
        try:
            # Validate against schema
            errors = sorted(self.validator.iter_errors(data), key=lambda e: e.path)

            if errors:
                error_messages = []
                for error in errors:
                    path = ".".join(str(p) for p in error.path) if error.path else "root"
                    error_messages.append(f"Path '{path}': {error.message}")

                return ValidationResult(False, error_messages)

            return ValidationResult(True)

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ValidationResult(False, [f"Validation failed: {str(e)}"])

    def get_schema(self) -> Dict[str, Any]:
        """Get validation schema."""
        return self.schema


class SchemaLoader:
    """Schema loader and cache manager."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize schema loader."""
        self.config = config or get_config()
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def load_schema(self, schema_path: Union[str, Path]) -> Dict[str, Any]:
        """Load schema from file with caching."""
        schema_path = Path(schema_path)
        cache_key = str(schema_path)

        # Check cache first
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        try:
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            with open(schema_path, 'r') as f:
                schema = json.load(f)

            # Validate the schema itself
            Draft7Validator.check_schema(schema)

            # Cache the schema
            self._schema_cache[cache_key] = schema
            logger.debug(f"Loaded schema from {schema_path}")

            return schema

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file {schema_path}: {e}")
        except jsonschema.SchemaError as e:
            raise ValueError(f"Invalid JSON schema in {schema_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load schema from {schema_path}: {e}")

    def get_test_type_schema(self, test_type: str) -> Dict[str, Any]:
        """Get schema for specific test type."""
        schema_path = self.config.paths.test_types_dir / test_type / "schema.json"
        return self.load_schema(schema_path)

    def get_environment_schema(self) -> Dict[str, Any]:
        """Get environment schema."""
        schema_path = self.config.paths.contracts_dir / "environment_schema.json"
        return self.load_schema(schema_path)

    def get_bom_schema(self, test_type: str) -> Dict[str, Any]:
        """Get BOM schema for specific test type."""
        schema_path = self.config.paths.test_types_dir / test_type / "bom_schema.json"
        return self.load_schema(schema_path)

    def clear_cache(self) -> None:
        """Clear schema cache."""
        self._schema_cache.clear()
        logger.debug("Schema cache cleared")


class TestResultValidator:
    """Validator for test results."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize test result validator."""
        self.config = config or get_config()
        self.schema_loader = SchemaLoader(config)

    def validate_test_results(self, test_type: str, results: Dict[str, Any]) -> ValidationResult:
        """Validate test results against test type schema."""
        try:
            schema = self.schema_loader.get_test_type_schema(test_type)
            validator = JSONSchemaValidator(schema)
            return validator.validate(results)
        except Exception as e:
            logger.error(f"Failed to validate test results for {test_type}: {e}")
            return ValidationResult(False, [f"Validation failed: {str(e)}"])

    def validate_environment(self, environment_data: Dict[str, Any]) -> ValidationResult:
        """Validate environment configuration."""
        try:
            schema = self.schema_loader.get_environment_schema()
            validator = JSONSchemaValidator(schema)
            return validator.validate(environment_data)
        except FileNotFoundError:
            # If no environment schema exists, perform basic validation
            return self._validate_basic_environment(environment_data)
        except Exception as e:
            logger.error(f"Failed to validate environment: {e}")
            return ValidationResult(False, [f"Environment validation failed: {str(e)}"])

    def validate_bom(self, test_type: str, bom_data: Dict[str, Any]) -> ValidationResult:
        """Validate BOM against test type BOM schema."""
        try:
            schema = self.schema_loader.get_bom_schema(test_type)
            validator = JSONSchemaValidator(schema)
            return validator.validate(bom_data)
        except FileNotFoundError:
            # If no BOM schema exists, perform basic validation
            return self._validate_basic_bom(bom_data)
        except Exception as e:
            logger.error(f"Failed to validate BOM for {test_type}: {e}")
            return ValidationResult(False, [f"BOM validation failed: {str(e)}"])

    def _validate_basic_environment(self, environment_data: Dict[str, Any]) -> ValidationResult:
        """Basic environment validation when no schema is available."""
        errors = []

        # Check required fields
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in environment_data:
                errors.append(f"Missing required field: {field}")

        # Check field types
        if 'name' in environment_data and not isinstance(environment_data['name'], str):
            errors.append("Field 'name' must be a string")

        if 'type' in environment_data and not isinstance(environment_data['type'], str):
            errors.append("Field 'type' must be a string")

        if 'tools' in environment_data and not isinstance(environment_data['tools'], dict):
            errors.append("Field 'tools' must be a dictionary")

        if 'metadata' in environment_data and not isinstance(environment_data['metadata'], dict):
            errors.append("Field 'metadata' must be a dictionary")

        return ValidationResult(len(errors) == 0, errors)

    def _validate_basic_bom(self, bom_data: Dict[str, Any]) -> ValidationResult:
        """Basic BOM validation when no schema is available."""
        errors = []

        # Check for hardware or software sections
        if 'hardware' not in bom_data and 'software' not in bom_data:
            errors.append("BOM must contain either 'hardware' or 'software' section")

        # Validate hardware section
        if 'hardware' in bom_data:
            hw = bom_data['hardware']
            if not isinstance(hw, dict):
                errors.append("Hardware section must be a dictionary")
            elif 'specs' not in hw:
                errors.append("Hardware section must contain 'specs'")

        # Validate software section
        if 'software' in bom_data:
            sw = bom_data['software']
            if not isinstance(sw, dict):
                errors.append("Software section must be a dictionary")
            elif 'specs' not in sw:
                errors.append("Software section must contain 'specs'")

        return ValidationResult(len(errors) == 0, errors)


class YAMLValidator:
    """YAML file validator."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize YAML validator."""
        self.config = config or get_config()
        self.result_validator = TestResultValidator(config)

    def validate_yaml_file(self, file_path: Path) -> ValidationResult:
        """Validate YAML file format and content."""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            if data is None:
                return ValidationResult(False, ["YAML file is empty"])

            return ValidationResult(True)

        except yaml.YAMLError as e:
            return ValidationResult(False, [f"Invalid YAML format: {e}"])
        except Exception as e:
            return ValidationResult(False, [f"Failed to read YAML file: {e}"])

    def validate_environment_file(self, file_path: Path) -> ValidationResult:
        """Validate environment YAML file."""
        # First validate YAML format
        yaml_result = self.validate_yaml_file(file_path)
        if not yaml_result.is_valid:
            return yaml_result

        # Then validate content
        try:
            with open(file_path, 'r') as f:
                environment_data = yaml.safe_load(f)

            return self.result_validator.validate_environment(environment_data)

        except Exception as e:
            return ValidationResult(False, [f"Failed to validate environment file: {e}"])

    def validate_bom_file(self, file_path: Path, test_type: str) -> ValidationResult:
        """Validate BOM YAML file."""
        # First validate YAML format
        yaml_result = self.validate_yaml_file(file_path)
        if not yaml_result.is_valid:
            return yaml_result

        # Then validate content
        try:
            with open(file_path, 'r') as f:
                bom_data = yaml.safe_load(f)

            return self.result_validator.validate_bom(test_type, bom_data)

        except Exception as e:
            return ValidationResult(False, [f"Failed to validate BOM file: {e}"])


class SchemaValidator:
    """Main schema validator facade."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize schema validator."""
        self.config = config or get_config()
        self.schema_loader = SchemaLoader(config)
        self.result_validator = TestResultValidator(config)
        self.yaml_validator = YAMLValidator(config)

    def validate_test_results(self, test_type: str, results: Dict[str, Any]) -> ValidationResult:
        """Validate test results."""
        return self.result_validator.validate_test_results(test_type, results)

    def validate_environment(self, environment_data: Dict[str, Any]) -> ValidationResult:
        """Validate environment data."""
        return self.result_validator.validate_environment(environment_data)

    def validate_bom(self, test_type: str, bom_data: Dict[str, Any]) -> ValidationResult:
        """Validate BOM data."""
        return self.result_validator.validate_bom(test_type, bom_data)

    def validate_environment_file(self, file_path: Path) -> ValidationResult:
        """Validate environment file."""
        return self.yaml_validator.validate_environment_file(file_path)

    def validate_bom_file(self, file_path: Path, test_type: str) -> ValidationResult:
        """Validate BOM file."""
        return self.yaml_validator.validate_bom_file(file_path, test_type)

    def is_test_type_supported(self, test_type: str) -> bool:
        """Check if test type is supported (has schema)."""
        try:
            schema_path = self.config.paths.test_types_dir / test_type / "schema.json"
            return schema_path.exists()
        except Exception:
            return False

    def get_supported_test_types(self) -> List[str]:
        """Get list of supported test types."""
        try:
            test_types = []
            for test_dir in self.config.paths.test_types_dir.iterdir():
                if test_dir.is_dir():
                    schema_file = test_dir / "schema.json"
                    if schema_file.exists():
                        test_types.append(test_dir.name)
            return sorted(test_types)
        except Exception as e:
            logger.error(f"Failed to get supported test types: {e}")
            return []

    def validate_all(self, test_type: str, results: Dict[str, Any],
                    environment_data: Optional[Dict[str, Any]] = None,
                    bom_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate all components together."""
        all_errors = []

        # Validate test results
        result_validation = self.validate_test_results(test_type, results)
        if not result_validation.is_valid:
            all_errors.extend([f"Test results: {error}" for error in result_validation.errors])

        # Validate environment if provided
        if environment_data:
            env_validation = self.validate_environment(environment_data)
            if not env_validation.is_valid:
                all_errors.extend([f"Environment: {error}" for error in env_validation.errors])

        # Validate BOM if provided
        if bom_data:
            bom_validation = self.validate_bom(test_type, bom_data)
            if not bom_validation.is_valid:
                all_errors.extend([f"BOM: {error}" for error in bom_validation.errors])

        return ValidationResult(len(all_errors) == 0, all_errors)

    def clear_cache(self) -> None:
        """Clear all validation caches."""
        self.schema_loader.clear_cache()
        logger.debug("Validation cache cleared")
