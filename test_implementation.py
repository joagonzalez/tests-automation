#!/usr/bin/env python3
"""
Test script to validate the benchmark analyzer implementation.

This script tests the main components of the benchmark analyzer:
- API endpoints
- Database connectivity
- CRUD operations
- File upload functionality
- Validation services

Run this script to check if the implementation is working correctly.
"""

import asyncio
import json
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List

import requests
import yaml


class ImplementationTester:
    """Test the benchmark analyzer implementation."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """Initialize the tester."""
        self.api_base_url = api_base_url.rstrip("/")
        self.test_results: List[Dict[str, Any]] = []
        self.created_resources: Dict[str, List[str]] = {
            "test_types": [],
            "environments": [],
            "test_runs": [],
            "uploads": []
        }

    def log_test(self, test_name: str, success: bool, message: str = "", details: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        if details and not success:
            print(f"    Details: {details}")

    def test_api_health(self) -> bool:
        """Test API health endpoints."""
        try:
            response = requests.get(f"{self.api_base_url}/health/", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                self.log_test(
                    "API Health Check",
                    True,
                    f"API is healthy: {health_data.get('status', 'unknown')}"
                )
                return True
            else:
                self.log_test(
                    "API Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    response.text
                )
                return False
        except Exception as e:
            self.log_test(
                "API Health Check",
                False,
                "Failed to connect to API",
                str(e)
            )
            return False

    def test_test_types_crud(self) -> bool:
        """Test test types CRUD operations."""
        try:
            # Create test type
            test_type_data = {
                "name": "implementation_test_type",
                "description": "Test type for implementation validation"
            }

            response = requests.post(
                f"{self.api_base_url}/api/v1/test-types/",
                json=test_type_data,
                timeout=10
            )

            if response.status_code != 201:
                self.log_test(
                    "Test Types - Create",
                    False,
                    f"Failed to create test type: {response.status_code}",
                    response.text
                )
                return False

            created_test_type = response.json()
            test_type_id = created_test_type["test_type_id"]
            self.created_resources["test_types"].append(test_type_id)

            self.log_test(
                "Test Types - Create",
                True,
                f"Created test type: {created_test_type['name']}"
            )

            # Read test type
            response = requests.get(
                f"{self.api_base_url}/api/v1/test-types/{test_type_id}",
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "Test Types - Read",
                    False,
                    f"Failed to read test type: {response.status_code}",
                    response.text
                )
                return False

            self.log_test(
                "Test Types - Read",
                True,
                "Successfully retrieved test type"
            )

            # Update test type
            update_data = {
                "description": "Updated description for implementation test"
            }

            response = requests.put(
                f"{self.api_base_url}/api/v1/test-types/{test_type_id}",
                json=update_data,
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "Test Types - Update",
                    False,
                    f"Failed to update test type: {response.status_code}",
                    response.text
                )
                return False

            self.log_test(
                "Test Types - Update",
                True,
                "Successfully updated test type"
            )

            # List test types
            response = requests.get(
                f"{self.api_base_url}/api/v1/test-types/",
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "Test Types - List",
                    False,
                    f"Failed to list test types: {response.status_code}",
                    response.text
                )
                return False

            test_types_list = response.json()
            self.log_test(
                "Test Types - List",
                True,
                f"Listed {test_types_list['total']} test types"
            )

            return True

        except Exception as e:
            self.log_test(
                "Test Types - CRUD",
                False,
                "Exception during test types CRUD test",
                str(e)
            )
            return False

    def test_environments_crud(self) -> bool:
        """Test environments CRUD operations."""
        try:
            # Create environment
            environment_data = {
                "name": "implementation_test_env",
                "type": "lab",
                "comments": "Environment for implementation testing",
                "tools": {
                    "sysbench": {
                        "version": "1.0.20",
                        "command": "sysbench"
                    }
                },
                "metadata": {
                    "location": "Test Lab",
                    "purpose": "validation"
                }
            }

            response = requests.post(
                f"{self.api_base_url}/api/v1/environments/",
                json=environment_data,
                timeout=10
            )

            if response.status_code != 201:
                self.log_test(
                    "Environments - Create",
                    False,
                    f"Failed to create environment: {response.status_code}",
                    response.text
                )
                return False

            created_environment = response.json()
            environment_id = created_environment["id"]
            self.created_resources["environments"].append(environment_id)

            self.log_test(
                "Environments - Create",
                True,
                f"Created environment: {created_environment['name']}"
            )

            # Test environment listing
            response = requests.get(
                f"{self.api_base_url}/api/v1/environments/",
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "Environments - List",
                    False,
                    f"Failed to list environments: {response.status_code}",
                    response.text
                )
                return False

            environments_list = response.json()
            self.log_test(
                "Environments - List",
                True,
                f"Listed {environments_list['total']} environments"
            )

            return True

        except Exception as e:
            self.log_test(
                "Environments - CRUD",
                False,
                "Exception during environments CRUD test",
                str(e)
            )
            return False

    def test_file_upload(self) -> bool:
        """Test file upload functionality."""
        try:
            # Create a test zip file
            zip_content = BytesIO()
            with zipfile.ZipFile(zip_content, 'w') as zf:
                test_data = {
                    "test_name": "implementation_validation_test",
                    "duration": 60,
                    "results": {
                        "cpu_score": 1500.0,
                        "memory_score": 8000.0
                    }
                }
                zf.writestr("test_data.json", json.dumps(test_data, indent=2))
                zf.writestr("metadata.txt", "Test file for implementation validation")

            zip_content.seek(0)

            # Upload file
            files = {
                "file": ("test_results.zip", zip_content, "application/zip")
            }
            data = {
                "file_type": "test_results"
            }

            response = requests.post(
                f"{self.api_base_url}/api/v1/upload/",
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                self.log_test(
                    "File Upload",
                    False,
                    f"Failed to upload file: {response.status_code}",
                    response.text
                )
                return False

            upload_response = response.json()
            upload_id = upload_response["upload_id"]
            self.created_resources["uploads"].append(upload_id)

            self.log_test(
                "File Upload",
                True,
                f"Successfully uploaded file: {upload_response['filename']}"
            )

            # Get file info
            response = requests.get(
                f"{self.api_base_url}/api/v1/upload/{upload_id}/info",
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "File Upload - Info",
                    False,
                    f"Failed to get file info: {response.status_code}",
                    response.text
                )
                return False

            self.log_test(
                "File Upload - Info",
                True,
                "Successfully retrieved file information"
            )

            return True

        except Exception as e:
            self.log_test(
                "File Upload",
                False,
                "Exception during file upload test",
                str(e)
            )
            return False

    def test_schema_upload(self) -> bool:
        """Test schema upload functionality."""
        try:
            # First, ensure we have a test type
            if not self.created_resources["test_types"]:
                self.log_test(
                    "Schema Upload",
                    False,
                    "No test types available for schema upload test"
                )
                return False

            test_type_id = self.created_resources["test_types"][0]

            # Create a test schema
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

            schema_file = BytesIO(json.dumps(schema_data, indent=2).encode())

            # Upload schema
            files = {
                "schema_file": ("test_schema.json", schema_file, "application/json")
            }

            response = requests.post(
                f"{self.api_base_url}/api/v1/test-types/{test_type_id}/schema",
                files=files,
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "Schema Upload",
                    False,
                    f"Failed to upload schema: {response.status_code}",
                    response.text
                )
                return False

            schema_response = response.json()
            self.log_test(
                "Schema Upload",
                True,
                f"Successfully uploaded schema for test type: {schema_response['name']}"
            )

            return True

        except Exception as e:
            self.log_test(
                "Schema Upload",
                False,
                "Exception during schema upload test",
                str(e)
            )
            return False

    def test_yaml_upload(self) -> bool:
        """Test YAML environment upload."""
        try:
            yaml_content = """
name: yaml_test_environment
type: lab
comments: Environment created from YAML upload test
tools:
  sysbench:
    version: "1.0.20"
    command: sysbench
    options:
      threads: 4
      time: 60
  stress:
    version: "1.0.4"
    command: stress-ng
metadata:
  location: Test Lab
  contact: test@example.com
  created_by: implementation_test
"""

            yaml_file = BytesIO(yaml_content.encode())

            files = {
                "environment_file": ("test_env.yaml", yaml_file, "application/x-yaml")
            }

            response = requests.post(
                f"{self.api_base_url}/api/v1/environments/upload",
                files=files,
                timeout=10
            )

            if response.status_code != 200:
                self.log_test(
                    "YAML Upload",
                    False,
                    f"Failed to upload YAML: {response.status_code}",
                    response.text
                )
                return False

            environment = response.json()
            environment_id = environment["id"]
            self.created_resources["environments"].append(environment_id)

            self.log_test(
                "YAML Upload",
                True,
                f"Successfully uploaded YAML environment: {environment['name']}"
            )

            return True

        except Exception as e:
            self.log_test(
                "YAML Upload",
                False,
                "Exception during YAML upload test",
                str(e)
            )
            return False

    def test_statistics_endpoints(self) -> bool:
        """Test statistics endpoints."""
        try:
            endpoints = [
                ("/api/v1/test-runs/stats/overview", "Test Runs Statistics"),
                ("/api/v1/environments/stats/overview", "Environments Statistics"),
                ("/api/v1/results/stats/overview", "Results Statistics"),
            ]

            all_passed = True

            for endpoint, name in endpoints:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)

                if response.status_code != 200:
                    self.log_test(
                        f"Statistics - {name}",
                        False,
                        f"Failed to get statistics: {response.status_code}",
                        response.text
                    )
                    all_passed = False
                else:
                    stats_data = response.json()
                    self.log_test(
                        f"Statistics - {name}",
                        True,
                        f"Successfully retrieved statistics"
                    )

            return all_passed

        except Exception as e:
            self.log_test(
                "Statistics Endpoints",
                False,
                "Exception during statistics test",
                str(e)
            )
            return False

    def cleanup_resources(self):
        """Clean up created test resources."""
        print("\n🧹 Cleaning up test resources...")

        # Clean up uploads
        for upload_id in self.created_resources["uploads"]:
            try:
                response = requests.delete(f"{self.api_base_url}/api/v1/upload/{upload_id}", timeout=10)
                if response.status_code == 200:
                    print(f"  ✅ Deleted upload: {upload_id}")
                else:
                    print(f"  ❌ Failed to delete upload: {upload_id}")
            except Exception as e:
                print(f"  ❌ Error deleting upload {upload_id}: {e}")

        # Clean up test runs
        for test_run_id in self.created_resources["test_runs"]:
            try:
                response = requests.delete(f"{self.api_base_url}/api/v1/test-runs/{test_run_id}", timeout=10)
                if response.status_code == 200:
                    print(f"  ✅ Deleted test run: {test_run_id}")
                else:
                    print(f"  ❌ Failed to delete test run: {test_run_id}")
            except Exception as e:
                print(f"  ❌ Error deleting test run {test_run_id}: {e}")

        # Clean up environments
        for environment_id in self.created_resources["environments"]:
            try:
                response = requests.delete(f"{self.api_base_url}/api/v1/environments/{environment_id}", timeout=10)
                if response.status_code == 200:
                    print(f"  ✅ Deleted environment: {environment_id}")
                else:
                    print(f"  ❌ Failed to delete environment: {environment_id}")
            except Exception as e:
                print(f"  ❌ Error deleting environment {environment_id}: {e}")

        # Clean up test types
        for test_type_id in self.created_resources["test_types"]:
            try:
                response = requests.delete(f"{self.api_base_url}/api/v1/test-types/{test_type_id}", timeout=10)
                if response.status_code == 200:
                    print(f"  ✅ Deleted test type: {test_type_id}")
                else:
                    print(f"  ❌ Failed to delete test type: {test_type_id}")
            except Exception as e:
                print(f"  ❌ Error deleting test type {test_type_id}: {e}")

    def run_all_tests(self) -> bool:
        """Run all tests."""
        print("🚀 Starting Benchmark Analyzer Implementation Tests")
        print("=" * 60)

        # Test API connectivity first
        if not self.test_api_health():
            print("\n❌ API is not accessible. Please ensure the API server is running.")
            return False

        print("\n📋 Running CRUD Tests...")
        test_results = [
            self.test_test_types_crud(),
            self.test_environments_crud(),
        ]

        print("\n📁 Running File Upload Tests...")
        test_results.extend([
            self.test_file_upload(),
            self.test_schema_upload(),
            self.test_yaml_upload(),
        ])

        print("\n📊 Running Statistics Tests...")
        test_results.append(self.test_statistics_endpoints())

        # Summary
        print("\n" + "=" * 60)
        print("📈 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")

        if passed == total:
            print("\n🎉 All tests passed! The implementation is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Please check the details above.")
            print("\nFailed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")

        return passed == total

    def run(self) -> bool:
        """Run the implementation test suite."""
        try:
            success = self.run_all_tests()
            return success
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            return False
        except Exception as e:
            print(f"\n\n❌ Unexpected error during testing: {e}")
            return False
        finally:
            self.cleanup_resources()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test the benchmark analyzer implementation")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup test resources after testing"
    )

    args = parser.parse_args()

    print("🔬 Benchmark Analyzer Implementation Tester")
    print("=" * 50)
    print(f"API URL: {args.api_url}")
    print(f"Cleanup: {'No' if args.no_cleanup else 'Yes'}")
    print()

    tester = ImplementationTester(args.api_url)

    try:
        success = tester.run()

        if not args.no_cleanup:
            print("\n🧹 Cleaning up...")
            tester.cleanup_resources()

        print("\n✨ Testing complete!")
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
