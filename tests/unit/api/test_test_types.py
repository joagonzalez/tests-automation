"""Unit tests for test types API endpoint."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from benchmark_analyzer.db.models import TestType, TestRun
from api.endpoints.test_types import router
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/test-types")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def sample_test_type():
    """Sample test type."""
    test_type = TestType(
        test_type_id="test-type-123",
        name="cpu_memory_test",
        description="CPU and memory performance test"
    )
    test_type.test_runs = []
    return test_type


@pytest.fixture
def sample_test_types():
    """Sample test types list."""
    test_types = [
        TestType(
            test_type_id="test-type-1",
            name="cpu_test",
            description="CPU performance test"
        ),
        TestType(
            test_type_id="test-type-2",
            name="memory_test",
            description="Memory performance test"
        )
    ]
    for tt in test_types:
        tt.test_runs = []
    return test_types


class TestListTestTypes:
    """Test list test types endpoint."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_list_test_types_success(self, mock_get_db, client, mock_session, sample_test_types):
        """Test successful test types listing."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.count.return_value = 2
        mock_query.offset.return_value.limit.return_value.all.return_value = sample_test_types
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "cpu_test"
        assert data["items"][1]["name"] == "memory_test"

    @patch('api.endpoints.test_types.get_db_session')
    def test_list_test_types_with_filters(self, mock_get_db, client, mock_session, sample_test_types):
        """Test test types listing with filters."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [sample_test_types[0]]
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/?name=cpu&sort_by=name&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @patch('api.endpoints.test_types.get_db_session')
    def test_list_test_types_pagination(self, mock_get_db, client, mock_session, sample_test_types):
        """Test test types listing with pagination."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.count.return_value = 2
        mock_query.offset.return_value.limit.return_value.all.return_value = [sample_test_types[0]]
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/?page=1&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["has_next"] is True
        assert data["has_prev"] is False

    @patch('api.endpoints.test_types.get_db_session')
    def test_list_test_types_database_error(self, mock_get_db, client, mock_session):
        """Test test types listing with database error."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock database error
        mock_session.query.side_effect = Exception("Database error")

        response = client.get("/test-types/")

        assert response.status_code == 500
        assert "Failed to list test types" in response.json()["detail"]


class TestGetTestType:
    """Test get test type endpoint."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_get_test_type_success(self, mock_get_db, client, mock_session, sample_test_type):
        """Test successful test type retrieval."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/test-type-123")

        assert response.status_code == 200
        data = response.json()
        assert data["test_type_id"] == "test-type-123"
        assert data["name"] == "cpu_memory_test"
        assert data["description"] == "CPU and memory performance test"

    @patch('api.endpoints.test_types.get_db_session')
    def test_get_test_type_not_found(self, mock_get_db, client, mock_session):
        """Test test type not found."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/non-existent-id")

        assert response.status_code == 404
        assert "Test type not found" in response.json()["detail"]


class TestCreateTestType:
    """Test create test type endpoint."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_create_test_type_success(self, mock_get_db, client, mock_session):
        """Test successful test type creation."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock existing check
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        test_type_data = {
            "name": "new_test_type",
            "description": "New test type description"
        }

        response = client.post("/test-types/", json=test_type_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_test_type"
        assert data["description"] == "New test type description"
        assert "test_type_id" in data

    @patch('api.endpoints.test_types.get_db_session')
    def test_create_test_type_duplicate_name(self, mock_get_db, client, mock_session, sample_test_type):
        """Test test type creation with duplicate name."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock existing check
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        test_type_data = {
            "name": "cpu_memory_test",
            "description": "Duplicate test type"
        }

        response = client.post("/test-types/", json=test_type_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_create_test_type_invalid_data(self, mock_get_db, client, mock_session):
        """Test test type creation with invalid data."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        test_type_data = {
            "description": "Missing name field"
        }

        response = client.post("/test-types/", json=test_type_data)

        assert response.status_code == 422  # Validation error


class TestUpdateTestType:
    """Test update test type endpoint."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_update_test_type_success(self, mock_get_db, client, mock_session, sample_test_type):
        """Test successful test type update."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query for existing test type
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        update_data = {
            "description": "Updated description"
        }

        response = client.put("/test-types/test-type-123", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["test_type_id"] == "test-type-123"

    @patch('api.endpoints.test_types.get_db_session')
    def test_update_test_type_not_found(self, mock_get_db, client, mock_session):
        """Test test type update with non-existent ID."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        update_data = {
            "description": "Updated description"
        }

        response = client.put("/test-types/non-existent-id", json=update_data)

        assert response.status_code == 404
        assert "Test type not found" in response.json()["detail"]


class TestDeleteTestType:
    """Test delete test type endpoint."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_delete_test_type_success(self, mock_get_db, client, mock_session, sample_test_type):
        """Test successful test type deletion."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        response = client.delete("/test-types/test-type-123")

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_delete_test_type_with_test_runs(self, mock_get_db, client, mock_session, sample_test_type):
        """Test test type deletion with associated test runs."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Add test runs to the test type
        test_run = TestRun(test_run_id="run-123", test_type_id="test-type-123")
        sample_test_type.test_runs = [test_run]

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        response = client.delete("/test-types/test-type-123")

        assert response.status_code == 400
        assert "associated test runs" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_delete_test_type_not_found(self, mock_get_db, client, mock_session):
        """Test test type deletion with non-existent ID."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        response = client.delete("/test-types/non-existent-id")

        assert response.status_code == 404
        assert "Test type not found" in response.json()["detail"]


class TestTestTypeSchema:
    """Test test type schema endpoints."""

    @patch('api.endpoints.test_types.get_db_session')
    def test_get_test_type_schema_not_implemented(self, mock_get_db, client, mock_session, sample_test_type):
        """Test get test type schema (not implemented)."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        response = client.get("/test-types/test-type-123/schema")

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_upload_test_type_schema_success(self, mock_get_db, client, mock_session, sample_test_type):
        """Test successful test type schema upload."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        # Create test schema file
        schema_content = {
            "type": "object",
            "properties": {
                "test_name": {"type": "string"},
                "duration": {"type": "integer"}
            },
            "required": ["test_name", "duration"]
        }

        schema_file = BytesIO(json.dumps(schema_content).encode())
        schema_file.name = "test_schema.json"

        response = client.post(
            "/test-types/test-type-123/schema",
            files={"schema_file": ("test_schema.json", schema_file, "application/json")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["test_type_id"] == "test-type-123"
        assert data["schema_uploaded"] is True

    @patch('api.endpoints.test_types.get_db_session')
    def test_upload_test_type_schema_invalid_file(self, mock_get_db, client, mock_session, sample_test_type):
        """Test test type schema upload with invalid file."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        # Create invalid file
        invalid_file = BytesIO(b"invalid content")
        invalid_file.name = "invalid.txt"

        response = client.post(
            "/test-types/test-type-123/schema",
            files={"schema_file": ("invalid.txt", invalid_file, "text/plain")}
        )

        assert response.status_code == 400
        assert "JSON file" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_upload_test_type_schema_invalid_json(self, mock_get_db, client, mock_session, sample_test_type):
        """Test test type schema upload with invalid JSON."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        # Create invalid JSON file
        invalid_json = BytesIO(b"{ invalid json }")
        invalid_json.name = "invalid.json"

        response = client.post(
            "/test-types/test-type-123/schema",
            files={"schema_file": ("invalid.json", invalid_json, "application/json")}
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_upload_test_type_schema_test_type_not_found(self, mock_get_db, client, mock_session):
        """Test test type schema upload with non-existent test type."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        schema_content = {"type": "object"}
        schema_file = BytesIO(json.dumps(schema_content).encode())
        schema_file.name = "test_schema.json"

        response = client.post(
            "/test-types/non-existent-id/schema",
            files={"schema_file": ("test_schema.json", schema_file, "application/json")}
        )

        assert response.status_code == 404
        assert "Test type not found" in response.json()["detail"]

    @patch('api.endpoints.test_types.get_db_session')
    def test_delete_test_type_schema_not_implemented(self, mock_get_db, client, mock_session, sample_test_type):
        """Test delete test type schema (not implemented)."""
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None

        # Mock query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_test_type
        mock_session.query.return_value = mock_query

        response = client.delete("/test-types/test-type-123/schema")

        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]


class TestValidation:
    """Test validation scenarios."""

    def test_create_test_type_validation(self, client):
        """Test test type creation validation."""
        # Test with missing name
        response = client.post("/test-types/", json={"description": "Test"})
        assert response.status_code == 422

        # Test with empty name
        response = client.post("/test-types/", json={"name": "", "description": "Test"})
        assert response.status_code == 422

        # Test with name too long
        long_name = "a" * 100
        response = client.post("/test-types/", json={"name": long_name, "description": "Test"})
        assert response.status_code == 422

    def test_update_test_type_validation(self, client):
        """Test test type update validation."""
        # Test with invalid data types
        response = client.put("/test-types/test-id", json={"name": 123})
        assert response.status_code == 422

        response = client.put("/test-types/test-id", json={"description": 123})
        assert response.status_code == 422

    def test_query_parameter_validation(self, client):
        """Test query parameter validation."""
        # Test with invalid page number
        response = client.get("/test-types/?page=0")
        assert response.status_code == 422

        # Test with invalid page size
        response = client.get("/test-types/?page_size=0")
        assert response.status_code == 422

        response = client.get("/test-types/?page_size=1001")
        assert response.status_code == 422

        # Test with invalid sort order
        response = client.get("/test-types/?sort_order=invalid")
        assert response.status_code == 422
