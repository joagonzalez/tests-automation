# CLI and API Architecture: Test Results Processing

This document explains how the benchmark analyzer CLI interacts with the API for processing test results, particularly ZIP file imports.

## Overview

The benchmark analyzer system has two main components:
- **CLI Tool** (`benchmark-analyzer`): Client-side tool for importing and managing test data
- **API Server** (`benchmark-api`): REST API for data storage and retrieval

## Test Results Import Architecture

### Current Implementation (CLI-Driven)

The CLI processes ZIP files **locally** and makes structured API calls to store data. This is the current and recommended approach.

#### Flow Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ZIP Package   │    │   CLI Tool      │    │   API Server    │
│   (Local File)  │    │   (Client)      │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. Read ZIP           │                       │
         ├──────────────────────►│                       │
         │                       │                       │
         │                       │ 2. Parse Locally     │
         │                       │    (ParserRegistry)   │
         │                       │                       │
         │                       │ 3. Validate Schema   │
         │                       │    (SchemaValidator)  │
         │                       │                       │
         │                       │ 4. Create Test Type   │
         │                       ├──────────────────────►│
         │                       │ 5. Create Environment │
         │                       ├──────────────────────►│
         │                       │ 6. Create BOM         │
         │                       ├──────────────────────►│
         │                       │ 7. Create Test Run    │
         │                       ├──────────────────────►│
         │                       │ 8. Store Results      │
         │                       ├──────────────────────►│
         │                       │                       │
         │                       │ 9. Return Test Run ID │
         │                       │◄──────────────────────┤
```

#### Command Usage

```bash
# Import test results with all metadata
benchmark-analyzer import \
    --package /path/to/results.zip \
    --type cpu_memory \
    --environment /path/to/environment.yaml \
    --bom /path/to/bom.yaml \
    --engineer "John Doe" \
    --comments "Performance baseline test"

# Validate only (don't import)
benchmark-analyzer import \
    --package /path/to/results.zip \
    --type cpu_memory \
    --validate-only
```

#### Code Flow

1. **CLI Entry Point** (`benchmark_analyzer/cli/main.py:import_results`)
   - Validates command arguments
   - Checks if test type is supported

2. **Local Processing**
   ```python
   # Parse the ZIP package locally
   parser = ParserRegistry.get_parser(test_type, config)
   results = parser.parse_package(package)
   
   # Validate against schemas
   validator = SchemaValidator(config)
   validation_result = validator.validate_test_results(test_type, result)
   ```

3. **API Integration** (`benchmark_analyzer/core/api_loader.py`)
   ```python
   # Make structured API calls
   api_loader.load_results(
       test_type=test_type,
       results=results,
       environment_file=environment,
       bom_file=bom,
       engineer=engineer,
       comments=comments
   )
   ```

4. **API Endpoints Called**
   - `POST /api/v1/test-types` - Create/get test type
   - `POST /api/v1/environments` - Create environment
   - `POST /api/v1/boms/hardware` - Create hardware BOM
   - `POST /api/v1/boms/software` - Create software BOM
   - `POST /api/v1/test-runs` - Create test run
   - `POST /api/v1/results/{test_run_id}` - Store results

### Alternative Implementation (Upload-Based)

There's also an upload endpoint that accepts file uploads, but it's **not currently used by the CLI**.

#### Available Upload Endpoints

```http
POST /api/v1/upload
Content-Type: multipart/form-data

# Upload a single file
file: <zip_file>
file_type: "test_results"
```

```http
POST /api/v1/upload/process/{upload_id}
Content-Type: application/json

# Process uploaded file
{
  "test_type": "cpu_memory",
  "environment_id": "env-123",
  "engineer": "John Doe",
  "comments": "Test run comments"
}
```

#### Why Upload Endpoint Isn't Used

1. **Incomplete Implementation**: The `process_uploaded_file` function has TODOs for actual result parsing
2. **Less Control**: Server-side processing provides less visibility into parsing/validation steps
3. **Network Overhead**: Requires uploading potentially large ZIP files
4. **Client-side Benefits**: Local processing allows for immediate validation feedback

## Configuration

### CLI Configuration

The CLI is configured via:
- Environment variables
- `.env` files (via `--env-file` option)
- Configuration classes in `benchmark_analyzer/config.py`

Key configuration:
```python
# API connection
API_BASE_URL=http://localhost:8000

# Database connection (for API)
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
```

### Entry Points

Defined in `pyproject.toml`:
```toml
[project.scripts]
benchmark-analyzer = "benchmark_analyzer.cli.main:app"
benchmark-api = "api.main:main"
```

## Components Overview

### CLI Components

```
benchmark_analyzer/
├── cli/
│   └── main.py              # Main CLI interface
├── core/
│   ├── api_client.py        # REST API client
│   ├── api_loader.py        # API-based data loader
│   ├── parser.py            # ZIP/file parsers
│   └── validator.py         # Schema validation
├── config.py                # Configuration management
└── db/                      # Database models (for API)
```

### API Components

```
api/
├── main.py                  # FastAPI application
├── endpoints/
│   ├── upload.py           # File upload endpoints
│   ├── test_runs.py        # Test run management
│   ├── results.py          # Results storage/retrieval
│   ├── test_types.py       # Test type management
│   ├── environments.py     # Environment management
│   └── boms.py            # BOM management
└── services/               # Business logic
```

## Data Flow Details

### 1. Test Type Management

```python
# CLI checks if test type exists
test_types = api_client.list_test_types()

# Creates new test type if needed
if not exists:
    test_type = api_client.create_test_type(name=test_type)
```

### 2. Environment Processing

```python
# Load environment YAML
with open(environment_file, 'r') as f:
    env_data = yaml.safe_load(f)

# Create via API
environment = api_client.create_environment(
    name=env_data.get("name"),
    env_type=env_data.get("type"),
    tools=env_data.get("tools", {}),
    comments=env_data.get("comments"),
    env_metadata=env_data.get("metadata", {})
)
```

### 3. Results Storage

```python
# Aggregate results for storage
aggregated_result = self._aggregate_cpu_mem_results(results)

# Store via API
api_client.create_results(test_run_id, aggregated_result)
```

## Error Handling

### CLI Error Handling

- **Validation Errors**: Displayed with detailed messages before import
- **API Errors**: Wrapped in `APILoaderError` with context
- **File Errors**: `ParseError` for invalid ZIP files or formats
- **Network Errors**: Retry logic in `APIClient` with exponential backoff

### API Error Responses

```json
{
  "error": true,
  "message": "Validation error",
  "details": [...],
  "status_code": 422
}
```

## Testing

### CLI Testing

```bash
# Test with validation only
benchmark-analyzer import --package test.zip --type cpu_memory --validate-only

# Check test types
benchmark-analyzer list-test-types

# Database status
benchmark-analyzer db status
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# List test runs
curl http://localhost:8000/api/v1/test-runs
```

## Future Enhancements

### Potential Upload Integration

To integrate the upload endpoint with CLI:

1. **Complete Upload Processing**
   ```python
   # In process_uploaded_file, implement:
   # 1. File type identification
   # 2. Parser selection and execution
   # 3. Schema validation
   # 4. Result storage
   ```

2. **CLI Upload Mode**
   ```bash
   benchmark-analyzer import --package test.zip --mode upload
   ```

3. **Progress Tracking**
   - WebSocket updates for upload progress
   - Polling endpoints for processing status

### Performance Optimizations

- **Streaming**: Large file streaming for uploads
- **Batch Processing**: Multiple result records in single API call
- **Caching**: Test type and environment caching
- **Compression**: Result data compression

## Troubleshooting

### Common Issues

1. **"Test type not supported"**
   ```bash
   # Check available test types
   benchmark-analyzer list-test-types
   ```

2. **"API connection failed"**
   ```bash
   # Check API status
   curl http://localhost:8000/health
   
   # Verify environment
   benchmark-analyzer --env-file .env import ...
   ```

3. **"Validation failed"**
   ```bash
   # Use validate-only mode to see errors
   benchmark-analyzer import --validate-only --package test.zip --type cpu_memory
   ```

### Debug Mode

```bash
# Enable verbose logging
benchmark-analyzer --verbose import --package test.zip --type cpu_memory
```

## Best Practices

1. **Always Validate First**: Use `--validate-only` before importing large datasets
2. **Environment Files**: Use consistent environment.yaml files for reproducible imports
3. **BOM Files**: Include BOM files for hardware/software traceability
4. **Error Handling**: Check CLI exit codes in automated scripts
5. **Monitoring**: Monitor API logs during bulk imports

---

*This document reflects the current architecture as of the latest codebase. The CLI-driven approach is the recommended method for importing test results.*