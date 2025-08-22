"""API-based loader for importing test results via REST endpoints."""

import json
import logging
import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .api_client import APIClient, APIClientError, get_api_client
from .parser import ParserRegistry, ParseError
from .validator import SchemaValidator, ValidationResult

logger = logging.getLogger(__name__)


class APILoaderError(Exception):
    """API loader error."""
    pass


class APILoader:
    """Loader that uses API endpoints instead of direct database access."""

    def __init__(self, config, api_base_url: str = None):
        """Initialize API loader."""
        self.config = config
        self.api_client = get_api_client(api_base_url)
        self.validator = SchemaValidator(config)

    def load_results(
        self,
        test_type: str,
        results: List[Dict[str, Any]],
        environment_file: Optional[Path] = None,
        bom_file: Optional[Path] = None,
        engineer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> str:
        """Load results using API endpoints."""
        try:
            # 1. Get or create test type
            test_type_obj = self._get_or_create_test_type(test_type)
            test_type_id = test_type_obj["test_type_id"]

            # 2. Process environment if provided
            environment_id = None
            if environment_file:
                environment_obj = self._load_environment(environment_file)
                environment_id = environment_obj["id"]

            # 3. Process BOM if provided
            hw_bom_id = None
            sw_bom_id = None
            if bom_file:
                hw_bom_id, sw_bom_id = self._load_bom(bom_file)

            # 4. Create test run
            test_run = self.api_client.create_test_run(
                test_type_id=test_type_id,
                environment_id=environment_id,
                hw_bom_id=hw_bom_id,
                sw_bom_id=sw_bom_id,
                engineer=engineer,
                comments=comments
            )
            test_run_id = test_run["test_run_id"]

            # 5. Store results
            self._store_results(test_run_id, results)

            logger.info(f"Successfully loaded {len(results)} results for test run {test_run_id}")
            return test_run_id

        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            raise APILoaderError(f"Failed to load results: {e}")

    def _get_or_create_test_type(self, test_type: str) -> Dict[str, Any]:
        """Get existing or create new test type."""
        try:
            # Try to find existing test type by name
            test_types_response = self.api_client.list_test_types()
            test_types = test_types_response.get("items", [])
            for tt in test_types:
                if tt.get("name") == test_type:
                    return tt

            # Create new test type if not found
            logger.info(f"Creating new test type: {test_type}")
            return self.api_client.create_test_type(name=test_type)

        except APIClientError as e:
            raise APILoaderError(f"Failed to get/create test type: {e}")

    def _load_environment(self, environment_file: Path) -> Dict[str, Any]:
        """Load environment from YAML file via API."""
        try:
            with open(environment_file, 'r') as f:
                env_data = yaml.safe_load(f)

            # Extract environment properties
            name = env_data.get("name", f"env_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            env_type = env_data.get("type", "unknown")
            tools = env_data.get("tools", {})
            comments = env_data.get("comments")
            env_metadata = env_data.get("metadata", {})

            # Check if environment with this name already exists
            environments_response = self.api_client.list_environments()
            environments = environments_response.get("items", [])
            for env in environments:
                if env.get("name") == name:
                    logger.info(f"Reusing existing environment: {name}")
                    return env

            # Create new environment
            logger.info(f"Creating new environment: {name}")
            return self.api_client.create_environment(
                name=name,
                env_type=env_type,
                tools=tools,
                comments=comments,
                env_metadata=env_metadata
            )

        except Exception as e:
            raise APILoaderError(f"Failed to load environment: {e}")

    def _load_bom(self, bom_file: Path) -> tuple[Optional[str], Optional[str]]:
        """Load BOM from YAML file via API."""
        try:
            with open(bom_file, 'r') as f:
                bom_data = yaml.safe_load(f)

            hw_bom_id = None
            sw_bom_id = None

            # Process hardware BOM
            if 'hardware' in bom_data:
                hw_specs = bom_data['hardware']
                hw_bom = self.api_client.create_or_get_hardware_bom(hw_specs)
                hw_bom_id = hw_bom["bom_id"]
                logger.info(f"Hardware BOM ID: {hw_bom_id}")

            # Process software BOM
            if 'software' in bom_data:
                sw_specs = bom_data['software']
                sw_bom = self.api_client.create_or_get_software_bom(sw_specs)
                sw_bom_id = sw_bom["bom_id"]
                logger.info(f"Software BOM ID: {sw_bom_id}")

            return hw_bom_id, sw_bom_id

        except Exception as e:
            raise APILoaderError(f"Failed to load BOM: {e}")

    def _store_results(self, test_run_id: str, results: List[Dict[str, Any]]) -> None:
        """Store results via API."""
        try:
            # Aggregate results (assuming CPU/memory test type for now)
            aggregated_result = self._aggregate_cpu_mem_results(results)

            # Store via API
            self.api_client.create_results(test_run_id, aggregated_result)
            logger.info(f"Stored aggregated results for test run {test_run_id}")

        except Exception as e:
            raise APILoaderError(f"Failed to store results: {e}")

    def _aggregate_cpu_mem_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate CPU/Memory results into a single record."""
        aggregated = {}

        for result in results:
            for key, value in result.items():
                if key in aggregated:
                    # For numeric values, take average
                    if isinstance(value, (int, float)) and isinstance(aggregated[key], (int, float)):
                        aggregated[key] = (aggregated[key] + value) / 2
                    else:
                        # For non-numeric, keep first value
                        continue
                else:
                    aggregated[key] = value

        return aggregated

    def list_test_runs(
        self,
        test_type: Optional[str] = None,
        environment: Optional[str] = None,
        engineer: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List test runs via API."""
        try:
            test_runs_response = self.api_client.list_test_runs(
                test_type=test_type,
                environment=environment,
                engineer=engineer,
                limit=limit,
                offset=offset
            )
            return test_runs_response.get("items", [])
        except APIClientError as e:
            raise APILoaderError(f"Failed to list test runs: {e}")

    def get_test_run_summary(self, test_run_id: str) -> Dict[str, Any]:
        """Get test run summary via API."""
        try:
            test_run = self.api_client.get_test_run(test_run_id)

            # Add results info if available
            try:
                results = self.api_client.get_results(test_run_id)
                test_run["has_results"] = True
                test_run["result_type"] = "cpu_mem"
            except:
                test_run["has_results"] = False

            return test_run

        except APIClientError as e:
            raise APILoaderError(f"Failed to get test run summary: {e}")
