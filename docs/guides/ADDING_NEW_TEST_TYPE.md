# How to Add a New Test Type to Benchmark Analyzer

This guide provides step-by-step instructions for adding a new test type to the benchmark analyzer framework. We'll use "network_perf" test as an example, which was recently implemented and tested.

## Overview

Adding a new test type involves:

1. **Database Model**: Create a new results model for storing test-specific metrics
2. **API Integration**: Update the results table mapping for dynamic API routing
3. **Parser Implementation**: Create and register a parser to process test result files
4. **Schema Definition**: Define JSON schemas that validate test results and BOM data
5. **Data Loader**: Add test type handling to the data loading system
6. **Example Data**: Create sample test data and supporting configurations
7. **Testing**: Validate the implementation works end-to-end

### Required Components
- Database model (`ResultsYourTestType`) - **REQUIRED**
- API table mapping entry - **REQUIRED**
- Parser class and registration - **REQUIRED**
- Test result schema (`schema.json`) - **REQUIRED**
- BOM schema (`bom_schema.json`) - **REQUIRED**
- Data loader integration - **REQUIRED**
- Example test data - **REQUIRED for testing**

### Optional Components
- Environment configuration - **RECOMMENDED**
- Custom validation logic - **OPTIONAL**
- Specialized BOM configuration - **RECOMMENDED**

> **Note**: This guide reflects the current CLI-API refactor where the CLI communicates with the database via the REST API, supporting both direct database access (development) and API-only access (production environments).

## Step-by-Step Implementation

### Step 1: Create Database Model

Create a new results model in `benchmark_analyzer/db/models.py`. Add this after the existing `ResultsCpuMem` class:

```python
class ResultsNetworkPerf(Base):
    """Results for Network Performance tests."""

    __tablename__ = "results_network_perf"

    test_run_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36),
        ForeignKey("test_runs.test_run_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Latency metrics (in milliseconds)
    tcp_latency_avg_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    tcp_latency_min_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    tcp_latency_max_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    udp_latency_avg_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    udp_latency_min_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    udp_latency_max_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)

    # Throughput metrics (in Mbps)
    tcp_throughput_mbps: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    udp_throughput_mbps: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    download_bandwidth_mbps: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    upload_bandwidth_mbps: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)

    # Connection metrics
    connection_establishment_time_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    connections_per_second: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Quality metrics
    packet_loss_percent: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    jitter_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)

    # Test configuration
    test_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    concurrent_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    packet_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_tool: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)

    # Relationships
    test_run = relationship("TestRun", back_populates="results_network_perf")

    def __repr__(self) -> str:
        return f"<ResultsNetworkPerf(test_run_id='{self.test_run_id}')>"
```

Also update the `TestRun` class to add the relationship:

```python
# Add this line in the TestRun class relationships section
results_network_perf = relationship("ResultsNetworkPerf", back_populates="test_run")
```

And update the `MODEL_REGISTRY`:

```python
MODEL_REGISTRY = {
    # ... existing models ...
    "results_network_perf": ResultsNetworkPerf,
}
```

### Step 2: Update API Integration

Update `api/endpoints/results.py` to include the new model:

```python
# Add the import
from benchmark_analyzer.db.models import (
    TestRun, TestType, Environment, ResultsCpuMem, ResultsNetworkPerf,
    HardwareBOM, SoftwareBOM
)

# Update the RESULTS_TABLE_MAP
RESULTS_TABLE_MAP = {
    'cpu_mem': ResultsCpuMem,
    'network_perf': ResultsNetworkPerf,
    # Add new test types here...
}
```

Also update `api/services/database.py` to include the import:

```python
from benchmark_analyzer.db.models import (
    Base, TestRun, TestType, Environment, HardwareBOM, SoftwareBOM,
    ResultsCpuMem, ResultsNetworkPerf, AcceptanceCriteria, Operator, MODEL_REGISTRY
)
```

### Step 3: Create Parser

Add the parser class to `benchmark_analyzer/core/parser.py`. Insert this before the `# Register default parsers` section:

```python
class NetworkPerfParser(JSONParser):
    """Parser for Network Performance benchmark results."""

    def get_test_type(self) -> str:
        """Get test type."""
        return "network_perf"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Network Performance result."""
        # Add timestamp if not present
        if 'timestamp' not in result:
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()

        return result

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate Network Performance result structure."""
        # Check for at least one network metric
        latency_metrics = [
            'tcp_latency_avg_ms', 'udp_latency_avg_ms',
            'tcp_latency_min_ms', 'udp_latency_min_ms'
        ]
        throughput_metrics = [
            'tcp_throughput_mbps', 'udp_throughput_mbps',
            'download_bandwidth_mbps', 'upload_bandwidth_mbps'
        ]
        connection_metrics = [
            'connection_establishment_time_ms', 'connections_per_second'
        ]
        quality_metrics = ['packet_loss_percent', 'jitter_ms']

        has_latency = any(metric in result for metric in latency_metrics)
        has_throughput = any(metric in result for metric in throughput_metrics)
        has_connection = any(metric in result for metric in connection_metrics)
        has_quality = any(metric in result for metric in quality_metrics)

        return has_latency or has_throughput or has_connection or has_quality
```

Then register the parser:

```python
ParserRegistry.register("network_perf", NetworkPerfParser)
```

### Step 4: Create Schema Validation Files

Create the directory structure:

```bash
mkdir -p benchmark_analyzer/contracts/tests/network_perf
```

Create `benchmark_analyzer/contracts/tests/network_perf/schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Network Performance Benchmark Test Results Schema",
  "description": "Schema for validating network performance benchmark test results",
  "properties": {
    "test_name": {
      "type": "string",
      "description": "Name of the test run",
      "minLength": 1,
      "maxLength": 255
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of when the test was executed"
    },
    "test_duration_sec": {
      "type": "integer",
      "description": "Total test duration in seconds",
      "minimum": 0
    },
    "tcp_latency_avg_ms": {
      "type": "number",
      "description": "Average TCP latency in milliseconds",
      "minimum": 0
    },
    "tcp_latency_min_ms": {
      "type": "number",
      "description": "Minimum TCP latency in milliseconds",
      "minimum": 0
    },
    "tcp_latency_max_ms": {
      "type": "number",
      "description": "Maximum TCP latency in milliseconds",
      "minimum": 0
    },
    "udp_latency_avg_ms": {
      "type": "number",
      "description": "Average UDP latency in milliseconds",
      "minimum": 0
    },
    "tcp_throughput_mbps": {
      "type": "number",
      "description": "TCP throughput in Mbps",
      "minimum": 0
    },
    "udp_throughput_mbps": {
      "type": "number",
      "description": "UDP throughput in Mbps",
      "minimum": 0
    },
    "download_bandwidth_mbps": {
      "type": "number",
      "description": "Download bandwidth in Mbps",
      "minimum": 0
    },
    "upload_bandwidth_mbps": {
      "type": "number",
      "description": "Upload bandwidth in Mbps",
      "minimum": 0
    },
    "connection_establishment_time_ms": {
      "type": "number",
      "description": "Connection establishment time in milliseconds",
      "minimum": 0
    },
    "connections_per_second": {
      "type": "integer",
      "description": "Number of connections established per second",
      "minimum": 0
    },
    "packet_loss_percent": {
      "type": "number",
      "description": "Packet loss percentage",
      "minimum": 0,
      "maximum": 100
    },
    "jitter_ms": {
      "type": "number",
      "description": "Network jitter in milliseconds",
      "minimum": 0
    },
    "test_tool": {
      "type": "string",
      "description": "Network testing tool used",
      "enum": ["iperf3", "netperf", "ping", "hping3", "nuttcp", "custom"]
    }
  },
  "required": [
    "test_name",
    "timestamp"
  ],
  "additionalProperties": true,
  "anyOf": [
    {"required": ["tcp_latency_avg_ms"]},
    {"required": ["udp_latency_avg_ms"]},
    {"required": ["tcp_throughput_mbps"]},
    {"required": ["udp_throughput_mbps"]},
    {"required": ["download_bandwidth_mbps"]},
    {"required": ["upload_bandwidth_mbps"]},
    {"required": ["connection_establishment_time_ms"]},
    {"required": ["connections_per_second"]},
    {"required": ["packet_loss_percent"]},
    {"required": ["jitter_ms"]}
  ]
}
```

Create `benchmark_analyzer/contracts/tests/network_perf/bom_schema.json` (copy from cpu_mem):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Bill of Materials Schema",
  "description": "Schema for validating BOM (Bill of Materials) files",
  "properties": {
    "hardware": {
      "type": "object",
      "description": "Hardware specifications",
      "properties": {
        "specs": {
          "type": "object",
          "description": "Hardware specifications",
          "additionalProperties": true
        }
      }
    },
    "software": {
      "type": "object", 
      "description": "Software specifications",
      "properties": {
        "specs": {
          "type": "object",
          "description": "Software specifications", 
          "additionalProperties": true
        }
      }
    }
  },
  "additionalProperties": true,
  "anyOf": [
    {"required": ["hardware"]},
    {"required": ["software"]}
  ]
}
```

### Step 5: Create Example Test Data

Create the test data directory:

```bash
mkdir -p examples/test_results/network_lab_run_001
```

Create `examples/test_results/network_lab_run_001/network_perf_results.json`:

```json
{
  "test_name": "lab_server_network_performance_001",
  "timestamp": "2024-01-15T14:30:00Z",
  "test_duration_sec": 300,
  "tcp_latency_avg_ms": 0.85,
  "tcp_latency_min_ms": 0.42,
  "tcp_latency_max_ms": 2.31,
  "udp_latency_avg_ms": 0.73,
  "udp_latency_min_ms": 0.38,
  "udp_latency_max_ms": 1.95,
  "tcp_throughput_mbps": 9850.0,
  "udp_throughput_mbps": 9720.0,
  "download_bandwidth_mbps": 9870.5,
  "upload_bandwidth_mbps": 9845.2,
  "connection_establishment_time_ms": 0.125,
  "connections_per_second": 15000,
  "packet_loss_percent": 0.001,
  "jitter_ms": 0.05,
  "concurrent_connections": 100,
  "packet_size_bytes": 1500,
  "test_tool": "iperf3",
  "test_parameters": {
    "protocol": "tcp/udp",
    "parallel_streams": 10,
    "window_size": "128KB",
    "buffer_length": "1M",
    "test_server": "192.168.10.200",
    "test_port": 5001,
    "reverse_mode": false
  },
  "error_count": 0,
  "warnings": [],
  "metadata": {
    "tool_version": "iperf-3.12",
    "os_info": "Ubuntu 22.04.3 LTS",
    "kernel_version": "5.15.0-88-generic",
    "network_interface": "ens3",
    "interface_speed": "10 Gbps",
    "mtu_size": 1500,
    "tcp_congestion_control": "cubic",
    "network_card": "Intel X710 10GbE",
    "driver_version": "2.19.3"
  }
}
```

Then create the ZIP package:

```bash
cd examples/test_results
zip -r lab_server_network_benchmark_001.zip network_lab_run_001/
```

### Step 6: Update Import Script

Update `examples/import_all_examples.sh` to include the new test type:

```bash
# Import Network Performance Results
print_status "Importing Network Performance benchmark results..."
if uv run benchmark-analyzer import-results \
    --package examples/test_results/lab_server_network_benchmark_001.zip \
    --type network_perf \
    --environment examples/environments/lab-server-network.yaml \
    --bom examples/boms/network-server.yaml \
    --engineer "Network Team" \
    --comments "High-performance network benchmark - Intel X710 10GbE"; then
    print_success "✓ Network Performance benchmark results imported successfully"
else
    print_error "Failed to import Network Performance benchmark results"
    exit 1
fi
```

### Step 7: Update Data Loader

Update the data loader in `benchmark_analyzer/core/loader.py`:

#### 7.1: Update imports

Add the new model import:
```python
from ..db.models import (
    Environment,
    HardwareBOM,
    SoftwareBOM,
    TestType,
    TestRun,
    ResultsCpuMem,
    ResultsNetworkPerf,  # Add this line
    calculate_specs_hash,
)
```

#### 7.2: Update the `_load_test_results` method

Find and update the test type routing:
```python
if test_type == "cpu_mem":
    self._load_cpu_mem_results(session, test_run, results)
elif test_type == "network_perf":  # Add this section
    self._load_network_perf_results(session, test_run, results)
else:
    # For other test types, we could dynamically create tables
    # For now, log a warning
    logger.warning(f"No specific loader for test type {test_type}, skipping results")
```

#### 7.3: Add the `_load_network_perf_results` method

Add this method after the `_load_cpu_mem_results` method:
```python
def _load_network_perf_results(
    self,
    session: Session,
    test_run: TestRun,
    results: List[Dict[str, Any]],
) -> None:
    """Load Network Performance results into results_network_perf table."""
    try:
        # Aggregate all results into a single record
        aggregated_result = self._aggregate_network_perf_results(results)

        network_perf_result = ResultsNetworkPerf(
            test_run_id=test_run.test_run_id,
            tcp_latency_avg_ms=aggregated_result.get('tcp_latency_avg_ms'),
            tcp_latency_min_ms=aggregated_result.get('tcp_latency_min_ms'),
            tcp_latency_max_ms=aggregated_result.get('tcp_latency_max_ms'),
            udp_latency_avg_ms=aggregated_result.get('udp_latency_avg_ms'),
            udp_latency_min_ms=aggregated_result.get('udp_latency_min_ms'),
            udp_latency_max_ms=aggregated_result.get('udp_latency_max_ms'),
            tcp_throughput_mbps=aggregated_result.get('tcp_throughput_mbps'),
            udp_throughput_mbps=aggregated_result.get('udp_throughput_mbps'),
            download_bandwidth_mbps=aggregated_result.get('download_bandwidth_mbps'),
            upload_bandwidth_mbps=aggregated_result.get('upload_bandwidth_mbps'),
            connection_establishment_time_ms=aggregated_result.get('connection_establishment_time_ms'),
            connections_per_second=aggregated_result.get('connections_per_second'),
            packet_loss_percent=aggregated_result.get('packet_loss_percent'),
            jitter_ms=aggregated_result.get('jitter_ms'),
            test_duration_sec=aggregated_result.get('test_duration_sec'),
            concurrent_connections=aggregated_result.get('concurrent_connections'),
            packet_size_bytes=aggregated_result.get('packet_size_bytes'),
            test_tool=aggregated_result.get('test_tool'),
        )

        session.add(network_perf_result)
        logger.debug(f"Added Network Performance results for test run {test_run.test_run_id}")

    except Exception as e:
        logger.error(f"Failed to load Network Performance results: {e}")
        raise
```

#### 7.4: Add the `_aggregate_network_perf_results` method

Add this method after the `_aggregate_cpu_mem_results` method:
```python
def _aggregate_network_perf_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multiple Network Performance results into a single record."""
    aggregated = {}

    for result in results:
        for key, value in result.items():
            if key.startswith(('tcp_', 'udp_', 'download_', 'upload_', 'connection_', 'packet_', 'jitter_', 'test_')):
                # For numeric values, take the last one or average if needed
                if isinstance(value, (int, float)):
                    aggregated[key] = value
                elif isinstance(value, str):
                    aggregated[key] = value

    return aggregated
```

#### 7.5: Update the `get_test_statistics` method

Update the statistics to include network performance results:
```python
stats = {
    'total_test_runs': session.query(TestRun).count(),
    'total_test_types': session.query(TestType).count(),
    'total_environments': session.query(Environment).count(),
    'total_hw_boms': session.query(HardwareBOM).count(),
    'total_sw_boms': session.query(SoftwareBOM).count(),
    'total_cpu_mem_results': session.query(ResultsCpuMem).count(),
    'total_network_perf_results': session.query(ResultsNetworkPerf).count(),  # Add this line
}
```

### Step 7: Create Example Test Data

Create the example directory structure:

```bash
mkdir -p examples/test_results/network_run_001
```

Create `examples/test_results/network_run_001/network_results.csv`:

```csv
test_name,timestamp,throughput_mbps,latency_ms,packet_loss_percent,test_duration_sec
network_iperf3_tcp_001,2024-01-15T10:30:00Z,940.5,0.245,0.01,60
```

### Step 7: Create Example Environment

Create `examples/environments/lab-server-network.yaml`:

```yaml
name: "lab-server-network"
type: "lab"
comments: "High-performance lab server optimized for network performance testing"

tools:
  iperf3:
    version: "3.12"
    command: "iperf3"
    options:
      port: 5001
      parallel: 10
      time: 60
      window: "128K"
      length: "1M"
  netperf:
    version: "2.7.0"
    command: "netperf"
    options:
      test_length: 60
      confidence_level: 95
      iterations: 5

metadata:
  location: "Lab A - Server Rack 2"
  rack: "LAB-A-R02"
  datacenter: "main-lab"
  environment_owner: "network-team"
  contact_email: "network-team@company.com"

  hardware:
    cpu_model: "Intel Xeon Gold 6230R"
    cpu_cores: 26
    memory_total: "128GB"
    network_interface: "10 Gigabit Ethernet"
    network_card: "Intel X710 Dual Port"
    network_ports: 2

  software:
    operating_system: "Ubuntu 22.04.3 LTS"
    kernel_version: "5.15.0-88-generic"
    container_runtime: "Docker 24.0.7"

  network:
    hostname: "lab-server-network"
    ip_address: "192.168.10.200"
    subnet: "192.168.10.0/24"
    gateway: "192.168.10.1"
    mtu: 1500
    tcp_congestion_control: "cubic"

  network_testing:
    test_server_ip: "192.168.10.201"
    available_bandwidth: "10Gbps"
    expected_latency_ms: 0.5

  tags:
    - "production"
    - "high-performance"
    - "network-benchmark"
    - "lab"
    - "10gbps"
```

### Step 8: Create Example BOM

Create `examples/boms/network-server.yaml`:

```yaml
hardware:
  specs:
    manufacturer: "Dell"
    model: "PowerEdge R650"
    network_adapter:
      model: "Intel X550-T2"
      ports: 2
      speed: "10GbE"
      interface: "RJ45"
    switch:
      model: "Cisco Catalyst 9300-48T"
      ports: "48x1GbE"
      uplinks: "4x10GbE"
    cables:
      type: "Cat6A"
      length: "3m"

software:
  specs:
    iperf_version: "3.12"
    driver_version: "5.13.0"
    network_stack: "Linux TCP/IP"
    kernel_version: "5.15.0-88-generic"
```

### Step 9: Package Test Data

Create the ZIP package for your test data:

```bash
cd examples/test_results
zip -r lab_server_network_benchmark_001.zip network_lab_run_001/
```

This creates the package that can be imported by the CLI tool.

### Step 13: Test the Implementation

1. **Verify parser registration**:
   ```bash
   uv run python -c "from benchmark_analyzer.core.parser import ParserRegistry; print('Available test types:', ParserRegistry.get_available_test_types())"
   ```

2. **Test database connection**:
   ```bash
   uv run benchmark-analyzer db status
   ```

3. **Import the test data**:
   ```bash
   uv run benchmark-analyzer import-results \
     --package examples/test_results/lab_server_network_benchmark_001.zip \
     --type network_perf \
     --environment examples/environments/lab-server-network.yaml \
     --bom examples/boms/network-server.yaml \
     --engineer "Network Team" \
     --comments "Network performance baseline test"
   ```

4. **Verify the import**:
   ```bash
   # Check database status
   uv run benchmark-analyzer db status
   
   # List test runs
   uv run benchmark-analyzer query test-runs --limit 5
   
   # List specific test type
   uv run benchmark-analyzer query test-runs --type network_perf
   ```

5. **Run the full import script**:
   ```bash
   ./examples/import_all_examples.sh
   ```

6. **Test the API** (if running):
   ```bash
   # Start the API infrastructure
   make dev-up
   
   # Test endpoints
   curl "http://localhost:8000/api/v1/results/?test_type=network_perf"
   curl "http://localhost:8000/api/v1/results/stats/overview"
   ```

## Validation and Testing

### Parser Registration Validation
Test that your parser is properly registered:

```bash
uv run python -c "from benchmark_analyzer.core.parser import ParserRegistry; print('Available test types:', ParserRegistry.get_available_test_types())"
```

### Schema Validation
The CLI tool automatically validates against your schema during import. Test with:

```bash
uv run benchmark-analyzer import-results \
  --package examples/test_results/lab_server_network_benchmark_001.zip \
  --type network_perf \
  --environment examples/environments/lab-server-network.yaml \
  --bom examples/boms/network-server.yaml \
  --engineer "Test Engineer" \
  --comments "Schema validation test"
```

### Database Integration Test
Verify your results are stored correctly:

```bash
# Check database status
uv run benchmark-analyzer db status

# Query your test type specifically
uv run benchmark-analyzer query test-runs --type network_perf
```

## Common Issues and Troubleshooting

1. **Test type not supported**: Ensure your parser is registered with `ParserRegistry.register()`
2. **Schema validation errors**: Check that your JSON data matches the schema exactly, especially required fields
3. **Database table creation**: Tables are created automatically via SQLAlchemy `Base.metadata.create_all()`
4. **API integration issues**: Verify your test type is added to `RESULTS_TABLE_MAP` in `api/endpoints/results.py`
5. **Import failures**: Check for missing BOM or environment schema files
6. **Data loader errors**: Ensure your loader method handles the aggregation correctly

## Best Practices

1. **Follow naming conventions**: Use descriptive test type names with underscores (e.g., `network_perf`, `io_perf`)
2. **Comprehensive database models**: Include all metrics you want to query efficiently
3. **Robust validation**: Check for at least one meaningful metric in your parser validation
4. **Realistic test data**: Use actual tool output values for believable examples
5. **Environment-specific configs**: Create dedicated environment and BOM files for your test type
6. **Update import scripts**: Add your test type to bulk import scripts for easy testing
7. **API compatibility**: Always update the `RESULTS_TABLE_MAP` for API integration

## File Summary

After completing this guide, you should have created or modified:

### Database Layer
- `benchmark_analyzer/db/models.py` - Added `ResultsNetworkPerf` model and relationships

### API Layer  
- `api/endpoints/results.py` - Added import and updated `RESULTS_TABLE_MAP`
- `api/services/database.py` - Added import for new model

### Parser Layer
- `benchmark_analyzer/core/parser.py` - Added `NetworkPerfParser` class and registration

### Data Layer
- `benchmark_analyzer/core/loader.py` - Added loader methods and statistics updates

### Schema Validation
- `benchmark_analyzer/contracts/tests/network_perf/schema.json` - Result validation schema
- `benchmark_analyzer/contracts/tests/network_perf/bom_schema.json` - BOM validation schema

### Example Data
- `examples/test_results/network_lab_run_001/network_perf_results.json` - Sample test data
- `examples/test_results/lab_server_network_benchmark_001.zip` - Packaged test data
- `examples/environments/lab-server-network.yaml` - Environment configuration
- `examples/boms/network-server.yaml` - BOM configuration

### Scripts
- `examples/import_all_examples.sh` - Updated to include new test type

This complete implementation provides a fully functional new test type that integrates with the existing CLI-API architecture.

Your new test type is now ready for use in the benchmark analyzer framework!