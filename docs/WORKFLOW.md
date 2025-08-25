# Benchmark Analyzer Data Loading Workflow

This document explains the complete workflow for loading and inserting test data into the benchmark analyzer framework, detailing the methods, classes, and validation processes involved.

## Overview

The data loading workflow consists of several key phases:
1. **Command Line Parsing & Initialization**
2. **Test Type & Parser Discovery**
3. **Package Parsing & Data Extraction**
4. **Schema Validation**
5. **Environment & BOM Loading**
6. **Database Operations**
7. **Results Storage**

## Detailed Workflow

### Phase 1: Command Line Parsing & Initialization

**Entry Point**: `benchmark_analyzer/cli/main.py::import_results()`

```python
@app.command()
def import_results(
    package: Path,
    test_type: str,
    environment: Optional[Path] = None,
    bom: Optional[Path] = None,
    engineer: Optional[str] = None,
    comments: Optional[str] = None,
    validate_only: bool = False,
):
```

**Steps**:
1. CLI validates command line arguments using Typer
2. Initializes global configuration via `get_config()`
3. Creates database manager via `get_db_manager()`
4. Sets up logging and rich console output

**Key Classes/Methods**:
- `Config::__init__()` - Loads environment variables and configuration
- `DatabaseManager::__init__()` - Initializes database connection
- `DatabaseManager::test_connection()` - Verifies database connectivity

### Phase 2: Test Type & Parser Discovery

**Location**: `benchmark_analyzer/cli/main.py::import_results()`

```python
if not ParserRegistry.is_test_type_supported(test_type):
    available_types = ParserRegistry.get_available_test_types()
    # Error handling
```

**Steps**:
1. Check if test type is registered in `ParserRegistry`
2. Get appropriate parser instance for the test type
3. Validate parser can handle the specified file types

**Key Classes/Methods**:
- `ParserRegistry::is_test_type_supported()` - Checks if test type has registered parser
- `ParserRegistry::get_parser()` - Returns parser instance for test type
- `ParserRegistry::get_available_test_types()` - Lists all registered parsers

**Parser Lookup Process**:
```python
# ParserRegistry maintains a dictionary of test_type -> parser_class
_parsers: Dict[str, Type[BaseParser]] = {
    "cpu_mem": CpuMemParser,
    "network": NetworkParser,
    "memory_bandwidth": MemoryBandwidthParser,
    # ... other parsers
}
```

### Phase 3: Package Parsing & Data Extraction

**Location**: `benchmark_analyzer/core/parser.py`

**Entry Method**: `BaseParser::parse_package()`

```python
def parse_package(self, package_path: Path) -> List[Dict[str, Any]]:
```

**Steps**:
1. **ZIP Detection**: Check if package is ZIP file or directory
2. **Extraction** (if ZIP):
   ```python
   with zipfile.ZipFile(package_path, 'r') as zip_ref:
       zip_ref.extractall(temp_dir)
   ```
3. **File Discovery**: Recursively find valid result files
4. **File Parsing**: Parse each valid file using parser-specific logic
5. **Result Aggregation**: Collect all parsed results into list

**Key Classes/Methods**:
- `BaseParser::parse_package()` - Main orchestration method
- `BaseParser::_is_valid_result_file()` - Checks file extension against supported types
- `BaseParser::parse_file()` - Abstract method implemented by specific parsers
- `CpuMemParser::parse_file()` - JSON parsing for CPU/Memory tests
- `NetworkParser::parse_file()` - CSV parsing for Network tests

**File Type Handling**:
```python
# Each parser defines supported extensions
def get_supported_extensions(self) -> List[str]:
    return ['.json']  # for CpuMemParser
    return ['.csv']   # for NetworkParser
```

### Phase 4: Schema Validation

**Location**: `benchmark_analyzer/core/validator.py`

**Entry Point**: `SchemaValidator::validate_test_results()`

```python
def validate_test_results(self, test_type: str, results: Dict[str, Any]) -> ValidationResult:
```

**Schema Discovery Process**:
1. **Schema Path Construction**:
   ```python
   schema_path = self.config.paths.test_types_dir / test_type / "schema.json"
   # Example: benchmark_analyzer/contracts/tests/network/schema.json
   ```

2. **Schema Loading**:
   ```python
   def load_schema(self, schema_path: Union[str, Path]) -> Dict[str, Any]:
       with open(schema_path, 'r') as f:
           schema = json.load(f)
       Draft7Validator.check_schema(schema)  # Validate schema itself
       return schema
   ```

3. **Schema Caching**:
   ```python
   self._schema_cache: Dict[str, Dict[str, Any]] = {}
   # Schemas are cached after first load for performance
   ```

**Validation Process**:
1. **Load Test Results Schema**: `test_types/{test_type}/schema.json`
2. **Validate Each Result**: Against JSON Schema using Draft7Validator
3. **Environment Validation** (if provided): Against `environment_schema.json`
4. **BOM Validation** (if provided): Against `test_types/{test_type}/bom_schema.json`

**Key Classes/Methods**:
- `SchemaLoader::load_schema()` - Loads and caches JSON schemas
- `JSONSchemaValidator::validate()` - Performs JSON schema validation
- `TestResultValidator::validate_test_results()` - Main validation orchestrator
- `YAMLValidator::validate_environment_file()` - Environment YAML validation
- `YAMLValidator::validate_bom_file()` - BOM YAML validation

### Phase 5: Environment & BOM Loading

**Location**: `benchmark_analyzer/core/loader.py`

#### 5.1: Environment Loading

**Method**: `DataLoader::_load_environment()`

```python
def _load_environment(self, session: Session, environment_file: Path) -> Environment:
```

**Process**:
1. **YAML Parsing**: Load and parse environment YAML file
2. **Duplicate Check**: Query database for existing environment with same name
3. **Create or Reuse**: Either return existing or create new environment record

**Environment Discovery**:
```python
env_name = env_data.get('name')
existing_env = session.query(Environment).filter_by(name=env_name).first()
```

#### 5.2: BOM Loading with Deduplication

**Method**: `DataLoader::_load_bom()`

```python
def _load_bom(self, session: Session, bom_file: Path) -> tuple[Optional[HardwareBOM], Optional[SoftwareBOM]]:
```

**Deduplication Process**:
1. **YAML Parsing**: Extract hardware and software specs
2. **Normalization**: Convert specs to normalized JSON for comparison
   ```python
   def _normalize_json_for_comparison(self, data: Dict[str, Any]) -> str:
       return json.dumps(data, sort_keys=True, separators=(',', ':'))
   ```
3. **Duplicate Detection**: Compare normalized specs against existing BOMs
4. **Create or Reuse**: Return existing BOM or create new one

**Key Classes/Methods**:
- `DataLoader::_find_existing_hw_bom()` - Searches for duplicate hardware BOMs
- `DataLoader::_find_existing_sw_bom()` - Searches for duplicate software BOMs
- `DataLoader::_normalize_json_for_comparison()` - Ensures consistent comparison

### Phase 6: Database Operations

**Location**: `benchmark_analyzer/core/loader.py`

#### 6.1: Test Type Management

**Method**: `DataLoader::_get_or_create_test_type()`

```python
def _get_or_create_test_type(self, session: Session, test_type_name: str) -> TestType:
```

**Process**:
1. Query for existing test type by name
2. Create new test type if not found
3. Generate UUID for new test type

#### 6.2: Test Run Creation

**Method**: `DataLoader::_create_test_run()`

```python
def _create_test_run(
    self,
    session: Session,
    test_type: TestType,
    environment: Optional[Environment],
    hw_bom: Optional[HardwareBOM],
    sw_bom: Optional[SoftwareBOM],
    engineer: Optional[str],
    comments: Optional[str],
) -> TestRun:
```

**Process**:
1. Generate UUID for test run
2. Create TestRun record with all foreign key relationships
3. Store metadata (engineer, comments, configuration)

### Phase 7: Results Storage

**Location**: `benchmark_analyzer/core/loader.py`

#### 7.1: Test Type Routing

**Method**: `DataLoader::_load_test_results()`

```python
def _load_test_results(
    self,
    session: Session,
    test_run: TestRun,
    test_type: str,
    results: List[Dict[str, Any]],
) -> None:
```

**Routing Logic**:
```python
if test_type == "cpu_mem":
    self._load_cpu_mem_results(session, test_run, results)
elif test_type == "network":
    self._load_network_results(session, test_run, results)
else:
    logger.warning(f"No specific loader for test type {test_type}")
```

#### 7.2: Test-Specific Result Loading

**CPU/Memory Results**: `DataLoader::_load_cpu_mem_results()`
- Aggregates multiple results into single record
- Maps to ResultsCpuMem table columns
- Stores metrics like memory bandwidth, CPU events, etc.

**Network Results**: `DataLoader::_load_network_results()`
- Aggregates network performance data
- Maps to ResultsNetwork table columns
- Stores metrics like throughput, latency, packet loss

**Aggregation Process**:
```python
def _aggregate_network_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    aggregated = {}
    for result in results:
        for key, value in result.items():
            if key in ['throughput_mbps', 'latency_ms', ...]:
                if isinstance(value, (int, float)):
                    aggregated[key] = value
    return aggregated
```

## Database Models & Relationships

### Core Entity Relationships

```
TestType (1) ──→ (N) TestRun (1) ──→ (1) ResultsCpuMem
                     │                └→ (1) ResultsNetwork
                     ├─→ (0..1) Environment
                     ├─→ (0..1) HardwareBOM
                     └─→ (0..1) SoftwareBOM
```

### Key Database Tables

1. **test_types**: Test type definitions (cpu_mem, network, etc.)
2. **test_runs**: Central fact table linking all components
3. **environments**: Test environment configurations
4. **hw_bom** / **sw_bom**: Bill of Materials for hardware/software
5. **results_cpu_mem**: CPU and memory specific results
6. **results_network**: Network specific results

## Error Handling & Rollback

### Transaction Management

All database operations are wrapped in transactions:

```python
with self.db_manager.get_session() as session:
    try:
        # All operations
        session.commit()
    except Exception as e:
        session.rollback()
        raise LoaderError(f"Failed to load results: {e}")
```

### Validation Failure Handling

1. **Schema Validation Fails**: Process stops before database operations
2. **Parser Errors**: Individual file failures logged, process continues
3. **Database Errors**: Full rollback, no partial data committed

## Configuration & Path Resolution

### Configuration Hierarchy

1. **Environment Variables**: Override all other settings
2. **`.env` File**: Project-specific overrides
3. **Default Values**: Built-in fallbacks

### Key Configuration Paths

```python
class PathConfig:
    base_dir: Path                    # Project root
    contracts_dir: Path               # Schema definitions
    test_types_dir: Path              # Test-specific schemas
    environments_dir: Path            # Environment templates
    artifacts_dir: Path               # Generated artifacts
    temp_dir: Path                    # Temporary processing
```

### Schema Resolution

```
Schema Path Pattern:
{base_dir}/benchmark_analyzer/contracts/tests/{test_type}/schema.json
{base_dir}/benchmark_analyzer/contracts/tests/{test_type}/bom_schema.json
{base_dir}/benchmark_analyzer/contracts/environment_schema.json
```

## Performance Considerations

### Caching Strategies

1. **Schema Caching**: Schemas loaded once and cached in memory
2. **BOM Deduplication**: Prevents duplicate BOM records
3. **Connection Pooling**: Database connections reused efficiently

### Batch Processing

- Multiple results from single package processed in single transaction
- Aggregation reduces database I/O operations
- Bulk validation before any database writes

## Extensibility Points

### Adding New Test Types

1. **Create Schema**: Add `contracts/tests/{new_type}/schema.json`
2. **Register Parser**: Add parser class and register in `ParserRegistry`
3. **Update Loader**: Add case in `_load_test_results()` method
4. **Add Database Model**: Create results table (optional)

### Custom Validation

1. **Extend Validators**: Inherit from `BaseValidator`
2. **Custom Business Rules**: Add to `ValidationService`
3. **Parser-Specific Logic**: Override validation methods in parser classes

## Monitoring & Logging

### Log Levels & Information

- **DEBUG**: Detailed processing information
- **INFO**: Major workflow steps and results
- **WARNING**: Non-fatal issues (missing optional fields)
- **ERROR**: Fatal errors causing process failure

### Key Metrics Logged

- Number of files processed
- Validation results
- Database operation results
- Performance timing information
- BOM deduplication statistics

This workflow ensures data integrity, prevents duplicates, and provides comprehensive validation while maintaining extensibility for new test types.
