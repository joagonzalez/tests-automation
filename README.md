# 🔧 Benchmark Analyzer Framework

A comprehensive framework for analyzing hardware and software benchmark results. The framework decouples the execution of performance, stress, and benchmark tests from the components that import, process, and display the results.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Configuration](#configuration)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

The Benchmark Analyzer Framework consists of two main components:

1. **benchmark-runner**: CLI for executing tests (developed by external team)
2. **benchmark-analyzer**: CLI and API for importing, processing, and analyzing results (this project)

This framework enables teams to:
- Execute benchmark tests in isolated environments
- Import and validate test results using flexible schemas
- Store results in a structured MySQL database
- Visualize and analyze results through Grafana dashboards
- Query and manage data via REST API

## ✨ Features

### Core Features
- 🔄 **Modular Test Result Processing**: Support for multiple test types with extensible parser system
- 📊 **Schema Validation**: JSON Schema-based validation for test results, environments, and BOMs
- 🗄️ **Database Storage**: MySQL-based storage with proper normalization and relationships
- 🌐 **REST API**: FastAPI-based API for CRUD operations and data management
- 📈 **Grafana Integration**: Pre-configured dashboards for result visualization
- 🔧 **CLI Interface**: Comprehensive command-line tools for data management

### Test Type Support
- **CPU/Memory Benchmarks**: Sysbench, RAMspeed, custom CPU tests
- **Extensible Parser System**: Easy addition of new test types
- **Environment Management**: Hardware and software BOM tracking
- **Result Validation**: Automated schema validation and error reporting

### Infrastructure
- 🐳 **Docker Compose**: Complete infrastructure stack
- 🔐 **Security**: Authentication, CORS, rate limiting
- 📝 **Comprehensive Logging**: Structured logging with multiple outputs
- 🚀 **Production Ready**: Health checks, monitoring, metrics

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test Operator  │    │  Test Analyst   │    │   Dashboard     │
│     (CLI)       │    │     (CLI)       │    │   (Grafana)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ benchmark-runner│    │benchmark-analyzer│   │   Grafana UI    │
│   (External)    │    │      CLI        │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test Results   │    │  REST API       │    │  MySQL Database │
│   (ZIP files)   │    │   (FastAPI)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Overview

- **CLI (benchmark-analyzer)**: Import results, manage data, query statistics
- **REST API**: CRUD operations, file uploads, data validation
- **Database Layer**: MySQL with SQLAlchemy ORM
- **Parser System**: Modular parsers for different test result formats
- **Validation Engine**: JSON Schema-based validation
- **Configuration Management**: Environment-based configuration

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- uv package manager (recommended)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd tests-automation

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup development environment
make setup
```

### 2. Start Infrastructure

```bash
# Start MySQL, Grafana, and API services
make dev
```

### 3. Import Sample Data

```bash
# Import test results
benchmark-analyzer import \
  --package examples/cpu_mem_results.zip \
  --type cpu_mem \
  --environment benchmark_analyzer/contracts/environments/dev/environment.yaml \
  --engineer "Your Name" \
  --comments "Sample benchmark results"
```

### 4. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **API Health**: http://localhost:8000/health

## 📦 Installation

### Using uv (Recommended)

```bash
# Development installation
uv pip install -e ".[dev]"

# Production installation
uv pip install -e .
```

### Using pip

```bash
# Development installation
pip install -e ".[dev]"

# Production installation
pip install -e .
```

### Docker Installation

```bash
# Build and run with Docker Compose
docker-compose -f infrastructure/docker-compose.yml up -d
```

## 💻 Usage

### CLI Usage

#### Database Management

```bash
# Initialize database
benchmark-analyzer db init

# Check database status
benchmark-analyzer db status

# Clean database (WARNING: Deletes all data)
benchmark-analyzer db clean --force
```

#### Importing Results

```bash
# Import CPU/Memory benchmark results
benchmark-analyzer import \
  --package test_results_20240115.zip \
  --type cpu_mem \
  --environment environments/production.yaml \
  --bom boms/server_config.yaml \
  --engineer "John Doe" \
  --comments "Production baseline test"

# Validate only (don't import)
benchmark-analyzer import \
  --package test_results.zip \
  --type cpu_mem \
  --validate-only
```

#### Querying Data

```bash
# List recent test runs
benchmark-analyzer query test-runs --limit 10

# Filter by test type
benchmark-analyzer query test-runs --type cpu_mem

# Filter by engineer
benchmark-analyzer query test-runs --engineer "John Doe"

# List available test types
benchmark-analyzer query test-types
```

#### Launching Dashboard

```bash
# Start Streamlit dashboard
benchmark-analyzer dashboard
```

### API Usage

#### Health Check

```bash
curl http://localhost:8000/health
```

#### List Test Runs

```bash
curl "http://localhost:8000/api/v1/test-runs?page=1&page_size=10"
```

#### Get Test Run Details

```bash
curl "http://localhost:8000/api/v1/test-runs/{test_run_id}"
```

#### Upload Test Results

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@test_results.zip" \
  -F "test_type=cpu_mem" \
  -F "engineer=John Doe"
```

### Python API Usage

```python
from benchmark_analyzer import get_config, get_db_manager
from benchmark_analyzer.core.loader import DataLoader
from benchmark_analyzer.core.parser import ParserRegistry

# Initialize components
config = get_config()
db_manager = get_db_manager()
loader = DataLoader(config, db_manager)

# Parse and load results
parser = ParserRegistry.get_parser("cpu_mem")
results = parser.parse_package("test_results.zip")
test_run_id = loader.load_results("cpu_mem", results)
```

## 📚 API Documentation

### REST API Endpoints

#### Health and Status
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with dependency status
- `GET /health/metrics` - Application metrics

#### Test Runs
- `GET /api/v1/test-runs` - List test runs with filtering and pagination
- `POST /api/v1/test-runs` - Create new test run
- `GET /api/v1/test-runs/{id}` - Get specific test run
- `PUT /api/v1/test-runs/{id}` - Update test run
- `DELETE /api/v1/test-runs/{id}` - Delete test run
- `GET /api/v1/test-runs/stats/overview` - Get test run statistics

#### Test Types
- `GET /api/v1/test-types` - List available test types
- `POST /api/v1/test-types` - Create new test type
- `GET /api/v1/test-types/{id}` - Get test type details

#### Environments
- `GET /api/v1/environments` - List environments
- `POST /api/v1/environments` - Create environment
- `GET /api/v1/environments/{id}` - Get environment details

#### File Upload
- `POST /api/v1/upload` - Upload and process test result files

### API Response Format

All API responses follow a consistent format:

```json
{
  "data": { ... },
  "message": "Success",
  "status_code": 200,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

Error responses:

```json
{
  "error": true,
  "message": "Error description",
  "details": { ... },
  "status_code": 400,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

## 🛠️ Development

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd tests-automation

# Setup development environment
make setup

# Start development infrastructure
make dev

# Run in development mode
make api-dev  # API with auto-reload
make dashboard  # Streamlit dashboard
```

### Available Make Commands

```bash
# Environment setup
make setup          # Setup development environment
make install        # Install dependencies
make update         # Update dependencies

# Code quality
make format         # Format code with ruff
make lint           # Lint code with ruff
make typecheck      # Run type checking with mypy
make check          # Run all quality checks

# Testing
make test           # Run all tests
make test-unit      # Run unit tests only
make test-integration  # Run integration tests only
make test-coverage  # Run tests with coverage

# Application
make cli            # Run CLI application
make api            # Run API server
make api-dev        # Run API with auto-reload
make dashboard      # Launch dashboard

# Database
make db-init        # Initialize database
make db-status      # Show database status
make db-clean       # Clean database

# Infrastructure
make infra-up       # Start infrastructure services
make infra-down     # Stop infrastructure services
make infra-logs     # Show infrastructure logs

# Development workflows
make dev            # Start full development environment
make dev-stop       # Stop development environment
make dev-reset      # Reset development environment

# Quality assurance
make qa             # Run full QA pipeline
make pre-commit     # Run pre-commit checks
make ci             # Run CI pipeline
```

### Adding New Test Types

1. **Create Schema**: Add JSON schema in `benchmark_analyzer/contracts/tests/{test_type}/schema.json`

2. **Create Parser**: Implement parser class extending `BaseParser`

```python
from benchmark_analyzer.core.parser import BaseParser, ParserRegistry

class NewTestTypeParser(BaseParser):
    def get_test_type(self) -> str:
        return "new_test_type"
    
    def get_supported_extensions(self) -> List[str]:
        return [".json", ".csv"]
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        # Implementation here
        pass

# Register parser
ParserRegistry.register("new_test_type", NewTestTypeParser)
```

3. **Create Database Model**: Add model in `benchmark_analyzer/db/models.py`

4. **Add API Endpoints**: Create endpoints in `api/endpoints/`

### Project Structure

```
tests-automation/
├── benchmark_analyzer/          # Main package
│   ├── cli/                    # CLI interface
│   ├── core/                   # Core components
│   │   ├── parser.py          # Parser system
│   │   ├── validator.py       # Schema validation
│   │   └── loader.py          # Data loading
│   ├── db/                    # Database layer
│   │   ├── models.py          # SQLAlchemy models
│   │   └── connector.py       # Database connection
│   ├── dashboards/            # Streamlit dashboards
│   ├── contracts/             # Schemas and contracts
│   │   ├── tests/            # Test type schemas
│   │   └── environments/     # Environment definitions
│   └── config.py              # Configuration management
├── api/                       # REST API
│   ├── endpoints/             # API endpoints
│   ├── services/              # Business logic services
│   └── config/                # API configuration
├── infrastructure/            # Docker and deployment
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                      # Documentation
├── Makefile                   # Development commands
└── pyproject.toml            # Project configuration
```

## ⚙️ Configuration

### Environment Variables

The framework uses environment variables for configuration. Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Key configuration sections:

#### Database Configuration
```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=benchmark
DB_PASSWORD=benchmark123
DB_NAME=perf_framework
```

#### API Configuration
```bash
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
SECRET_KEY=your-secret-key
```

#### Security Configuration
```bash
ENABLE_AUTH=false
CORS_ORIGINS=*
```

### Configuration Files

#### YAML Configuration
```yaml
# config.yaml
database:
  host: localhost
  port: 3306
  username: benchmark
  password: benchmark123
api:
  host: 0.0.0.0
  port: 8000
  debug: false
```

#### Environment Contracts
```yaml
# environments/production.yaml
name: "production"
type: "production"
tools:
  python: "3.11.7"
  sysbench: "1.0.20"
metadata:
  location: "datacenter-1"
  hardware:
    cpu_model: "Intel Xeon Gold 6230R"
    memory_total: "128GB"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test categories
make test-unit
make test-integration

# Run specific test file
uv run pytest tests/unit/test_config.py -v

# Run with specific markers
uv run pytest -m "unit" -v
uv run pytest -m "integration" -v
uv run pytest -m "database" -v
```

### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **API Tests**: Test REST API endpoints
- **Database Tests**: Test database operations

### Test Configuration

Tests use a separate test database and configuration:

```python
# tests/conftest.py
@pytest.fixture
def test_config():
    return {
        "database": {
            "database": "test_perf_framework",
            "host": "localhost"
        }
    }
```

### Writing Tests

```python
import pytest
from benchmark_analyzer.core.parser import ParserRegistry

class TestCpuMemParser:
    def test_parse_valid_json(self):
        parser = ParserRegistry.get_parser("cpu_mem")
        result = parser.parse_file("test_data/valid_result.json")
        assert result["test_name"] == "cpu_test_001"
    
    @pytest.mark.integration
    def test_database_integration(self, test_db):
        # Integration test with database
        pass
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. **Fork and Clone**
```bash
git clone <your-fork>
cd tests-automation
```

2. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

3. **Setup Development Environment**
```bash
make setup
make dev
```

4. **Make Changes**
- Follow code style guidelines
- Add tests for new functionality
- Update documentation

5. **Run Quality Checks**
```bash
make pre-commit
```

6. **Submit Pull Request**
- Ensure all tests pass
- Update CHANGELOG.md
- Add clear description

### Code Style

- **Python**: Follow PEP 8, use ruff for formatting and linting
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings
- **Testing**: Maintain >90% test coverage

### Commit Messages

Use conventional commit format:
```
feat: add new CPU benchmark parser
fix: resolve database connection timeout
docs: update API documentation
test: add integration tests for loader
```

## 📝 Changelog

### [0.1.0] - 2024-01-15

#### Added
- Initial framework implementation
- CLI interface for importing and querying results
- REST API with FastAPI
- MySQL database with SQLAlchemy models
- JSON Schema validation system
- Modular parser system for test results
- Docker Compose infrastructure
- Comprehensive test suite
- Configuration management system
- Development tooling and CI/CD

#### Supported Test Types
- CPU/Memory benchmarks (Sysbench, RAMspeed)
- Extensible parser framework for future test types

#### Infrastructure
- MySQL 8.4 database
- Grafana 10.2 dashboards
- FastAPI REST API
- Docker containerization

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- **API Docs**: http://localhost:8000/docs (when running)
- **Project Wiki**: [GitHub Wiki](link-to-wiki)
- **Examples**: Check `examples/` directory

### Getting Help
- **Issues**: [GitHub Issues](link-to-issues)
- **Discussions**: [GitHub Discussions](link-to-discussions)
- **Email**: benchmark-analyzer@company.com

### Troubleshooting

#### Common Issues

**Database Connection Failed**
```bash
# Check if MySQL is running
make infra-logs

# Verify database configuration
benchmark-analyzer config-info

# Test database connection
benchmark-analyzer db status
```

**Import Validation Errors**
```bash
# Validate files before import
benchmark-analyzer import --validate-only --package results.zip --type cpu_mem

# Check available test types
benchmark-analyzer query test-types
```

**API Not Responding**
```bash
# Check API health
curl http://localhost:8000/health

# View API logs
make infra-logs

# Restart API service
make api-dev
```

#### Performance Optimization

- **Database**: Tune MySQL configuration for your workload
- **API**: Adjust worker count and connection pooling
- **Caching**: Enable Redis caching for frequently accessed data

---

**Built with ❤️ by the Benchmark Analyzer Team**