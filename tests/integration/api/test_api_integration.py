"""Integration tests for API endpoints."""

import json
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from benchmark_analyzer.db.models import TestType, Environment, TestRun


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""

    def test_complete_workflow(self, api_client: TestClient):
        """Test complete workflow from test type creation to results query."""
        # 1. Create a test type
        test_type_data = {
            "name": "integration_test_type",
            "description": "Integration test type"
        }
        response = api_client.post("/api/v1/test-types/", json=test_type_data)
        assert response.status_code == 201
        test_type = response.json()
        test_type_id = test_type["test_type_id"]

        # 2. Create an environment
        environment_data = {
            "name": "integration_test_env",
            "type": "lab",
            "comments": "Integration test environment",
            "tools": {
                "sysbench": {
                    "version": "1.0.20",
                    "command": "sysbench"
                }
            }
        }
        response = api_client.post("/api/v1/environments/", json=environment_data)
        assert response.status_code == 201
        environment = response.json()
        environment_id = environment["id"]

        # 3. Create a test run
        test_run_data = {
            "test_type_id": test_type_id,
            "environment_id": environment_id,
            "engineer": "Integration Tester",
            "comments": "Integration test run"
        }
        response = api_client.post("/api/v1/test-runs/", json=test_run_data)
        assert response.status_code == 201
        test_run = response.json()
        test_run_id = test_run["test_run_id"]

        # 4. Verify test run details
        response = api_client.get(f"/api/v1/test-runs/{test_run_id}")
        assert response.status_code == 200
        retrieved_test_run = response.json()
        assert retrieved_test_run["test_type_id"] == test_type_id
        assert retrieved_test_run["environment_id"] == environment_id
        assert retrieved_test_run["engineer"] == "Integration Tester"

        # 5. List test types and verify our test type is there
        response = api_client.get("/api/v1/test-types/")
        assert response.status_code == 200
        test_types = response.json()
        assert any(tt["test_type_id"] == test_type_id for tt in test_types["items"])

        # 6. List environments and verify our environment is there
        response = api_client.get("/api/v1/environments/")
        assert response.status_code == 200
        environments = response.json()
        assert any(env["id"] == environment_id for env in environments["items"])

        # 7. List test runs and verify our test run is there
        response = api_client.get("/api/v1/test-runs/")
        assert response.status_code == 200
        test_runs = response.json()
        assert any(tr["test_run_id"] == test_run_id for tr in test_runs["items"])

        # 8. Update test run
        update_data = {
            "comments": "Updated integration test run",
            "engineer": "Updated Integration Tester"
        }
        response = api_client.put(f"/api/v1/test-runs/{test_run_id}", json=update_data)
        assert response.status_code == 200
        updated_test_run = response.json()
        assert updated_test_run["comments"] == "Updated integration test run"
        assert updated_test_run["engineer"] == "Updated Integration Tester"

        # 9. Clean up - delete test run first
        response = api_client.delete(f"/api/v1/test-runs/{test_run_id}")
        assert response.status_code == 200

        # 10. Clean up - delete environment
        response = api_client.delete(f"/api/v1/environments/{environment_id}")
        assert response.status_code == 200

        # 11. Clean up - delete test type
        response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
        assert response.status_code == 200

    def test_file_upload_workflow(self, api_client: TestClient):
        """Test file upload workflow."""
        # Create a test zip file
        zip_content = BytesIO()
        with zipfile.ZipFile(zip_content, 'w') as zf:
            test_data = {
                "test_name": "upload_test",
                "duration": 60,
                "results": {
                    "cpu_score": 1500.0,
                    "memory_score": 8000.0
                }
            }
            zf.writestr("test_data.json", json.dumps(test_data))
        zip_content.seek(0)

        # Upload file
        response = api_client.post(
            "/api/v1/upload/",
            files={"file": ("test_results.zip", zip_content, "application/zip")},
            data={"file_type": "test_results"}
        )
        assert response.status_code == 200
        upload_response = response.json()
        upload_id = upload_response["upload_id"]

        # Get file info
        response = api_client.get(f"/api/v1/upload/{upload_id}/info")
        assert response.status_code == 200
        file_info = response.json()
        assert file_info["upload_id"] == upload_id
        assert file_info["filename"] == "test_results.zip"
        assert file_info["file_type"] == "test_results"

        # List uploaded files
        response = api_client.get("/api/v1/upload/")
        assert response.status_code == 200
        uploaded_files = response.json()
        assert any(f["upload_id"] == upload_id for f in uploaded_files)

        # Clean up - delete uploaded file
        response = api_client.delete(f"/api/v1/upload/{upload_id}")
        assert response.status_code == 200

    def test_validation_errors(self, api_client: TestClient):
        """Test validation error handling."""
        # Test invalid test type creation
        response = api_client.post("/api/v1/test-types/", json={"description": "Missing name"})
        assert response.status_code == 422

        # Test invalid environment creation
        response = api_client.post("/api/v1/environments/", json={"type": "invalid_type"})
        assert response.status_code == 422

        # Test invalid test run creation
        response = api_client.post("/api/v1/test-runs/", json={"engineer": "No test type"})
        assert response.status_code == 422

    def test_not_found_errors(self, api_client: TestClient):
        """Test not found error handling."""
        # Test getting non-existent test type
        response = api_client.get("/api/v1/test-types/non-existent-id")
        assert response.status_code == 404

        # Test getting non-existent environment
        response = api_client.get("/api/v1/environments/non-existent-id")
        assert response.status_code == 404

        # Test getting non-existent test run
        response = api_client.get("/api/v1/test-runs/non-existent-id")
        assert response.status_code == 404

        # Test getting non-existent uploaded file
        response = api_client.get("/api/v1/upload/non-existent-id/info")
        assert response.status_code == 404

    def test_business_logic_validation(self, api_client: TestClient):
        """Test business logic validation."""
        # 1. Create a test type
        test_type_data = {
            "name": "business_logic_test",
            "description": "Business logic test type"
        }
        response = api_client.post("/api/v1/test-types/", json=test_type_data)
        assert response.status_code == 201
        test_type = response.json()
        test_type_id = test_type["test_type_id"]

        # 2. Try to create duplicate test type
        response = api_client.post("/api/v1/test-types/", json=test_type_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

        # 3. Create a test run using the test type
        test_run_data = {
            "test_type_id": test_type_id,
            "engineer": "Business Logic Tester"
        }
        response = api_client.post("/api/v1/test-runs/", json=test_run_data)
        assert response.status_code == 201
        test_run = response.json()
        test_run_id = test_run["test_run_id"]

        # 4. Try to delete test type that has associated test runs
        response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
        assert response.status_code == 400
        assert "associated test runs" in response.json()["detail"]

        # 5. Clean up - delete test run first
        response = api_client.delete(f"/api/v1/test-runs/{test_run_id}")
        assert response.status_code == 200

        # 6. Now delete test type should work
        response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
        assert response.status_code == 200

    def test_schema_upload_workflow(self, api_client: TestClient):
        """Test schema upload workflow."""
        # 1. Create a test type
        test_type_data = {
            "name": "schema_test_type",
            "description": "Schema test type"
        }
        response = api_client.post("/api/v1/test-types/", json=test_type_data)
        assert response.status_code == 201
        test_type = response.json()
        test_type_id = test_type["test_type_id"]

        # 2. Upload schema
        schema_data = {
            "type": "object",
            "properties": {
                "test_name": {"type": "string"},
                "duration": {"type": "integer", "minimum": 1},
                "results": {
                    "type": "object",
                    "properties": {
                        "cpu_score": {"type": "number"},
                        "memory_score": {"type": "number"}
                    },
                    "required": ["cpu_score", "memory_score"]
                }
            },
            "required": ["test_name", "duration", "results"]
        }

        schema_file = BytesIO(json.dumps(schema_data).encode())
        response = api_client.post(
            f"/api/v1/test-types/{test_type_id}/schema",
            files={"schema_file": ("test_schema.json", schema_file, "application/json")}
        )
        assert response.status_code == 200
        schema_response = response.json()
        assert schema_response["schema_uploaded"] is True

        # 3. Try to upload invalid schema
        invalid_schema = BytesIO(b"{ invalid json }")
        response = api_client.post(
            f"/api/v1/test-types/{test_type_id}/schema",
            files={"schema_file": ("invalid.json", invalid_schema, "application/json")}
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

        # 4. Clean up
        response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
        assert response.status_code == 200

    def test_environment_yaml_upload(self, api_client: TestClient):
        """Test environment YAML upload."""
        yaml_content = """
name: yaml_upload_test_env
type: lab
comments: Environment created from YAML upload
tools:
  sysbench:
    version: "1.0.20"
    command: sysbench
    options:
      threads: 4
      time: 60
metadata:
  location: Test Lab
  contact: test@example.com
"""

        yaml_file = BytesIO(yaml_content.encode())
        response = api_client.post(
            "/api/v1/environments/upload",
            files={"environment_file": ("test_env.yaml", yaml_file, "application/x-yaml")}
        )
        assert response.status_code == 200
        environment = response.json()
        assert environment["name"] == "yaml_upload_test_env"
        assert environment["type"] == "lab"
        assert "sysbench" in environment["tools"]

        # Clean up
        response = api_client.delete(f"/api/v1/environments/{environment['id']}")
        assert response.status_code == 200

    def test_bulk_file_upload(self, api_client: TestClient):
        """Test bulk file upload."""
        # Create multiple test files
        files = []
        for i in range(3):
            zip_content = BytesIO()
            with zipfile.ZipFile(zip_content, 'w') as zf:
                test_data = {
                    "test_name": f"bulk_test_{i}",
                    "duration": 60,
                    "results": {"cpu_score": 1500.0 + i * 100}
                }
                zf.writestr(f"test_data_{i}.json", json.dumps(test_data))
            zip_content.seek(0)
            files.append(("files", (f"test_results_{i}.zip", zip_content, "application/zip")))

        # Upload files
        response = api_client.post(
            "/api/v1/upload/bulk",
            files=files,
            data={"file_type": "test_results"}
        )
        assert response.status_code == 200
        bulk_response = response.json()
        assert bulk_response["successful_uploads"] == 3
        assert bulk_response["failed_uploads"] == 0
        assert len(bulk_response["upload_ids"]) == 3

        # Clean up uploaded files
        for upload_id in bulk_response["upload_ids"]:
            response = api_client.delete(f"/api/v1/upload/{upload_id}")
            assert response.status_code == 200

    def test_statistics_endpoints(self, api_client: TestClient):
        """Test statistics endpoints."""
        # Create test data
        test_type_data = {
            "name": "stats_test_type",
            "description": "Statistics test type"
        }
        response = api_client.post("/api/v1/test-types/", json=test_type_data)
        assert response.status_code == 201
        test_type = response.json()
        test_type_id = test_type["test_type_id"]

        environment_data = {
            "name": "stats_test_env",
            "type": "lab"
        }
        response = api_client.post("/api/v1/environments/", json=environment_data)
        assert response.status_code == 201
        environment = response.json()
        environment_id = environment["id"]

        test_run_data = {
            "test_type_id": test_type_id,
            "environment_id": environment_id,
            "engineer": "Stats Tester"
        }
        response = api_client.post("/api/v1/test-runs/", json=test_run_data)
        assert response.status_code == 201
        test_run = response.json()
        test_run_id = test_run["test_run_id"]

        # Test test run statistics
        response = api_client.get("/api/v1/test-runs/stats/overview")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_runs"] >= 1
        assert "runs_by_type" in stats
        assert "runs_by_engineer" in stats

        # Test environment statistics
        response = api_client.get("/api/v1/environments/stats/overview")
        assert response.status_code == 200
        env_stats = response.json()
        assert env_stats["total_environments"] >= 1
        assert "environments_by_type" in env_stats

        # Test results statistics
        response = api_client.get("/api/v1/results/stats/overview")
        assert response.status_code == 200
        results_stats = response.json()
        assert "total_results" in results_stats

        # Clean up
        response = api_client.delete(f"/api/v1/test-runs/{test_run_id}")
        assert response.status_code == 200
        response = api_client.delete(f"/api/v1/environments/{environment_id}")
        assert response.status_code == 200
        response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
        assert response.status_code == 200

    def test_pagination_and_filtering(self, api_client: TestClient):
        """Test pagination and filtering."""
        # Create multiple test types
        test_type_ids = []
        for i in range(5):
            test_type_data = {
                "name": f"pagination_test_{i}",
                "description": f"Pagination test type {i}"
            }
            response = api_client.post("/api/v1/test-types/", json=test_type_data)
            assert response.status_code == 201
            test_type_ids.append(response.json()["test_type_id"])

        # Test pagination
        response = api_client.get("/api/v1/test-types/?page=1&page_size=2")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["items"]) == 2
        assert page1["has_next"] is True
        assert page1["has_prev"] is False

        response = api_client.get("/api/v1/test-types/?page=2&page_size=2")
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["items"]) == 2
        assert page2["has_next"] is True
        assert page2["has_prev"] is True

        # Test filtering
        response = api_client.get("/api/v1/test-types/?name=pagination_test_1")
        assert response.status_code == 200
        filtered = response.json()
        assert len(filtered["items"]) == 1
        assert filtered["items"][0]["name"] == "pagination_test_1"

        # Test sorting
        response = api_client.get("/api/v1/test-types/?sort_by=name&sort_order=desc")
        assert response.status_code == 200
        sorted_results = response.json()
        # Should be sorted in descending order
        names = [item["name"] for item in sorted_results["items"]]
        assert names == sorted(names, reverse=True)

        # Clean up
        for test_type_id in test_type_ids:
            response = api_client.delete(f"/api/v1/test-types/{test_type_id}")
            assert response.status_code == 200

    def test_health_endpoints(self, api_client: TestClient):
        """Test health endpoints."""
        # Test basic health check
        response = api_client.get("/health/")
        assert response.status_code == 200
        health = response.json()
        assert health["status"] == "healthy"
        assert "timestamp" in health

        # Test detailed health check
        response = api_client.get("/health/detailed")
        assert response.status_code == 200
        detailed_health = response.json()
        assert detailed_health["status"] == "healthy"
        assert "checks" in detailed_health

        # Test liveness probe
        response = api_client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

        # Test readiness probe
        response = api_client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

        # Test metrics endpoint
        response = api_client.get("/health/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert "timestamp" in metrics
        assert "database" in metrics
