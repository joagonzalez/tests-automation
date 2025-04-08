from pathlib import Path
import json
from typing import Dict, Any, Optional
import jsonschema
import logging
from benchmark_analyzer.config import Config

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates test results against JSON schemas."""

    def __init__(self, test_type: str):
        """
        Initialize the schema validator.

        Args:
            test_type (str): The type of test to validate (e.g., 'memory_bandwidth', 'cpu_latency')
        """
        self.test_type = test_type
        self.config = Config()
        self.schema = self._load_schema()
        logger.debug(f"Initialized SchemaValidator for test type: {test_type}")

    def _load_schema(self) -> Dict[str, Any]:
        """
        Load JSON schema for the test type from the contracts directory.

        Returns:
            Dict[str, Any]: The loaded schema as a dictionary

        Raises:
            FileNotFoundError: If the schema file doesn't exist
            json.JSONDecodeError: If the schema file is not valid JSON
        """
        # Construct schema path
        schema_path = (
            Path(self.config.contracts_path) / 
            "tests" / 
            self.test_type / 
            "schema.json"
        )

        logger.debug(f"Looking for schema at: {schema_path}")

        if not schema_path.exists():
            error_msg = (
                f"Schema not found for test type: {self.test_type}\n"
                f"Expected path: {schema_path}\n"
                f"Please ensure the schema file exists and the path is correct."
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(schema_path) as f:
                schema = json.load(f)
                logger.debug(f"Successfully loaded schema for {self.test_type}")
                return schema
        except json.JSONDecodeError as e:
            error_msg = (
                f"Invalid JSON in schema file: {schema_path}\n"
                f"Error: {str(e)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate data against the schema.

        Args:
            data (Dict[str, Any]): The data to validate

        Returns:
            bool: True if validation succeeds

        Raises:
            ValueError: If validation fails with details about the failure
        """
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            logger.debug(f"Validation successful for test type: {self.test_type}")
            return True
        except jsonschema.exceptions.ValidationError as e:
            error_msg = (
                f"Validation error for test type {self.test_type}:\n"
                f"Path: {' -> '.join(str(p) for p in e.path)}\n"
                f"Message: {e.message}\n"
                f"Schema path: {' -> '.join(str(p) for p in e.schema_path)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except jsonschema.exceptions.SchemaError as e:
            error_msg = f"Invalid schema for test type {self.test_type}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def validate_with_format(
        self, 
        data: Dict[str, Any], 
        format_validators: Optional[Dict[str, callable]] = None
    ) -> bool:
        """
        Validate data with custom format validators.

        Args:
            data (Dict[str, Any]): The data to validate
            format_validators (Optional[Dict[str, callable]]): Custom format validators

        Returns:
            bool: True if validation succeeds

        Raises:
            ValueError: If validation fails with details about the failure
        """
        format_checker = jsonschema.FormatChecker()
        
        # Register custom format validators if provided
        if format_validators:
            for format_name, validator in format_validators.items():
                format_checker.checks(format_name)(validator)

        try:
            jsonschema.validate(
                instance=data,
                schema=self.schema,
                format_checker=format_checker
            )
            logger.debug(
                f"Validation with custom formats successful for test type: {self.test_type}"
            )
            return True
        except jsonschema.exceptions.ValidationError as e:
            error_msg = (
                f"Validation error for test type {self.test_type}:\n"
                f"Path: {' -> '.join(str(p) for p in e.path)}\n"
                f"Message: {e.message}\n"
                f"Schema path: {' -> '.join(str(p) for p in e.schema_path)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def get_schema(self) -> Dict[str, Any]:
        """
        Get the loaded schema.

        Returns:
            Dict[str, Any]: The currently loaded schema
        """
        return self.schema

    def get_required_fields(self) -> list[str]:
        """
        Get list of required fields from the schema.

        Returns:
            list[str]: List of required field names
        """
        return self.schema.get("required", [])

    def get_field_type(self, field_name: str) -> Optional[str]:
        """
        Get the type of a specific field from the schema.

        Args:
            field_name (str): Name of the field

        Returns:
            Optional[str]: Type of the field if it exists in the schema
        """
        properties = self.schema.get("properties", {})
        if field_name in properties:
            return properties[field_name].get("type")
        return None