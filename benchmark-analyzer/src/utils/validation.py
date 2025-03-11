from typing import Dict, Any
from pathlib import Path
import yaml
import jsonschema

class ResultsValidator:
    """Validator for benchmark results"""
    
    @staticmethod
    def validate_benchmark_results(results: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate benchmark results against schema"""
        try:
            jsonschema.validate(instance=results, schema=schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Invalid benchmark results: {e}")

    @staticmethod
    def validate_environment_config(config_path: Path) -> Dict:
        """Validate environment configuration file"""
        schema = {
            "type": "object",
            "required": ["name", "type", "resources", "credentials"],
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "resources": {
                    "type": "object",
                    "required": ["cpu", "memory"],
                    "properties": {
                        "cpu": {"type": "integer"},
                        "memory": {"type": "string"}
                    }
                },
                "credentials": {
                    "type": "object",
                    "required": ["username", "password", "host", "port", "database"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "database": {"type": "string"}
                    }
                }
            }
        }

        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        try:
            jsonschema.validate(instance=config, schema=schema)
            return config
        except jsonschema.exceptions.ValidationError as e:
            raise ValueError(f"Invalid environment configuration: {e}")