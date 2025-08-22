"""API client for CLI to interact with REST endpoints."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """API client error."""
    pass


class APIClient:
    """Simple API client for benchmark analyzer."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """Initialize API client."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise APIClientError(f"API request failed: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    # Test Types
    def list_test_types(self) -> List[Dict[str, Any]]:
        """List all test types."""
        return self._request("GET", "/api/v1/test-types")

    def create_test_type(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new test type."""
        data = {"name": name}
        if description:
            data["description"] = description
        return self._request("POST", "/api/v1/test-types", json=data)

    def get_test_type(self, test_type_id: str) -> Dict[str, Any]:
        """Get test type by ID."""
        return self._request("GET", f"/api/v1/test-types/{test_type_id}")

    # Environments
    def list_environments(self) -> List[Dict[str, Any]]:
        """List all environments."""
        return self._request("GET", "/api/v1/environments")

    def create_environment(self, name: str, env_type: str = None, tools: Dict[str, Any] = None,
                          comments: str = None, env_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new environment."""
        data = {"name": name}
        if env_type:
            data["type"] = env_type
        if tools:
            data["tools"] = tools
        if comments:
            data["comments"] = comments
        if env_metadata:
            data["env_metadata"] = env_metadata
        return self._request("POST", "/api/v1/environments", json=data)

    def get_environment(self, environment_id: str) -> Dict[str, Any]:
        """Get environment by ID."""
        return self._request("GET", f"/api/v1/environments/{environment_id}")

    # BOMs
    def create_or_get_hardware_bom(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """Create or get existing hardware BOM."""
        return self._request("POST", "/api/v1/boms/hardware", json={"specs": specs})

    def create_or_get_software_bom(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """Create or get existing software BOM."""
        return self._request("POST", "/api/v1/boms/software", json={"specs": specs})

    def get_hardware_bom(self, bom_id: str) -> Dict[str, Any]:
        """Get hardware BOM by ID."""
        return self._request("GET", f"/api/v1/boms/hardware/{bom_id}")

    def get_software_bom(self, bom_id: str) -> Dict[str, Any]:
        """Get software BOM by ID."""
        return self._request("GET", f"/api/v1/boms/software/{bom_id}")

    # Test Runs
    def list_test_runs(self, test_type: str = None, environment: str = None,
                       engineer: str = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """List test runs with filtering."""
        params = {"limit": limit, "offset": offset}
        if test_type:
            params["test_type"] = test_type
        if environment:
            params["environment"] = environment
        if engineer:
            params["engineer"] = engineer
        return self._request("GET", "/api/v1/test-runs", params=params)

    def create_test_run(self, test_type_id: str, environment_id: str = None,
                       hw_bom_id: str = None, sw_bom_id: str = None,
                       engineer: str = None, comments: str = None,
                       configuration: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new test run."""
        data = {"test_type_id": test_type_id}
        if environment_id:
            data["environment_id"] = environment_id
        if hw_bom_id:
            data["hw_bom_id"] = hw_bom_id
        if sw_bom_id:
            data["sw_bom_id"] = sw_bom_id
        if engineer:
            data["engineer"] = engineer
        if comments:
            data["comments"] = comments
        if configuration:
            data["configuration"] = configuration
        return self._request("POST", "/api/v1/test-runs", json=data)

    def get_test_run(self, test_run_id: str) -> Dict[str, Any]:
        """Get test run by ID."""
        return self._request("GET", f"/api/v1/test-runs/{test_run_id}")

    # Results
    def create_results(self, test_run_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create results for a test run."""
        return self._request("POST", f"/api/v1/results/{test_run_id}", json={"results": results})

    def get_results(self, test_run_id: str) -> Dict[str, Any]:
        """Get results for a test run."""
        return self._request("GET", f"/api/v1/results/{test_run_id}")

    def get_results_stats(self) -> Dict[str, Any]:
        """Get results statistics."""
        return self._request("GET", "/api/v1/results/stats/overview")

    # File Upload
    def upload_file(self, file_path: Union[str, Path], file_type: str) -> Dict[str, Any]:
        """Upload a file to the API."""
        file_path = Path(file_path)

        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            data = {'file_type': file_type}

            # Don't use _request for file uploads
            url = f"{self.base_url}/api/v1/upload"
            response = self.session.post(url, files=files, data=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

    def import_package(self, package_path: Union[str, Path], test_type: str,
                      environment_file: Union[str, Path] = None,
                      bom_file: Union[str, Path] = None,
                      engineer: str = None, comments: str = None) -> Dict[str, Any]:
        """Import a complete test package via API."""
        try:
            import_data = {
                "test_type": test_type,
                "engineer": engineer,
                "comments": comments
            }

            # Upload package file
            package_result = self.upload_file(package_path, "test_results")
            import_data["package_file"] = package_result["file_path"]

            # Upload environment file if provided
            if environment_file:
                env_result = self.upload_file(environment_file, "environment")
                import_data["environment_file"] = env_result["file_path"]

            # Upload BOM file if provided
            if bom_file:
                bom_result = self.upload_file(bom_file, "bom")
                import_data["bom_file"] = bom_result["file_path"]

            # Trigger import process
            return self._request("POST", "/api/v1/upload/import", json=import_data)

        except Exception as e:
            logger.error(f"Package import failed: {e}")
            raise APIClientError(f"Package import failed: {e}")


def get_api_client(base_url: str = None) -> APIClient:
    """Get API client instance."""
    if base_url is None:
        # Try to get from environment or config
        import os
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    return APIClient(base_url)
