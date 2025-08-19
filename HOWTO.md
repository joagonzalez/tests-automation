# How to Add a New Test Type to Benchmark Analyzer

This guide provides step-by-step instructions for adding a new test type to the benchmark analyzer framework. We'll use a simple "network" test as an example.

## Overview

Adding a new test type involves:

1. **Schema Definition**: Define JSON schemas that validate test results and BOM data
2. **Parser Implementation**: Create a parser to process test result files
3. **Example Data**: Create sample test data and supporting files
4. **Testing**: Validate the implementation works end-to-end

### Required Components
- Test result schema (`schema.json`) - **REQUIRED**
- Parser class registration - **REQUIRED**
- Example test data - **REQUIRED for testing**

### Optional Components
- BOM schema (`bom_schema.json`) - **OPTIONAL**
- Environment configuration - **OPTIONAL**
- Custom validation logic - **OPTIONAL**

## Step-by-Step Implementation

### Step 1: Create the Test Type Directory Structure

Create the directory structure for your new test type:

```bash
mkdir -p benchmark_analyzer/contracts/tests/network
```

### Step 2: Define the Test Result Schema

Create `benchmark_analyzer/contracts/tests/network/schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Network Performance Test Results Schema",
  "description": "Schema for validating network performance test results",
  "properties": {
    "test_name": {
      "type": "string",
      "description": "Name of the network test",
      "minLength": 1
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of test execution"
    },
    "throughput_mbps": {
      "type": "number",
      "description": "Network throughput in Mbps",
      "minimum": 0
    },
    "latency_ms": {
      "type": "number",
      "description": "Network latency in milliseconds",
      "minimum": 0
    },
    "packet_loss_percent": {
      "type": "number",
      "description": "Packet loss percentage",
      "minimum": 0,
      "maximum": 100
    },
    "test_duration_sec": {
      "type": "integer",
      "description": "Test duration in seconds",
      "minimum": 1
    }
  },
  "required": ["test_name", "timestamp", "throughput_mbps"],
  "additionalProperties": true
}
```

### Step 3: Create BOM Schema (Optional)

Create `benchmark_analyzer/contracts/tests/network/bom_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Network Test BOM Schema",
  "description": "Schema for network test Bill of Materials",
  "properties": {
    "hardware": {
      "type": "object",
      "properties": {
        "specs": {
          "type": "object",
          "properties": {
            "network_adapter": {"type": "string"},
            "port_speed": {"type": "string"},
            "switch_model": {"type": "string"}
          }
        }
      }
    },
    "software": {
      "type": "object",
      "properties": {
        "specs": {
          "type": "object",
          "properties": {
            "iperf_version": {"type": "string"},
            "driver_version": {"type": "string"}
          }
        }
      }
    }
  },
  "additionalProperties": true
}
```

### Step 4: Create Network Parser

Add the following parser class to `benchmark_analyzer/core/parser.py`. Insert this code before the `# Register default parsers` section:

```python
class NetworkParser(CSVParser):
    """Parser for network performance test results."""

    def get_test_type(self) -> str:
        """Get test type."""
        return "network"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize network result."""
        # Add timestamp if not present
        if 'timestamp' not in result:
            from datetime import datetime
            result['timestamp'] = datetime.now().isoformat()

        # Ensure required fields exist
        required_fields = ['test_name', 'throughput_mbps']
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field '{field}' in network result")

        return result

    def validate_result_structure(self, result: Dict[str, Any]) -> bool:
        """Validate network result structure."""
        required_fields = ['test_name', 'throughput_mbps']
        return all(field in result for field in required_fields)
```

Then register the parser by adding this line to the registration section at the bottom:

```python
ParserRegistry.register("network", NetworkParser)
```

### Step 5: Create Database Model (Optional)

If you need custom database fields, create a new model in `benchmark_analyzer/db/models.py`. For the network test type, you would add:

```python
class ResultsNetwork(Base):
    """Results for Network performance tests."""

    __tablename__ = "results_network"

    test_run_id: Mapped[str] = mapped_column(
        MYSQL_CHAR(36),
        ForeignKey("test_runs.test_run_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Network metrics
    throughput_mbps: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    packet_loss_percent: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    test_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional network metrics
    jitter_ms: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    bandwidth_utilization_percent: Mapped[Optional[float]] = mapped_column(DOUBLE, nullable=True)
    connection_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    test_run = relationship("TestRun", back_populates="results_network")

    def __repr__(self) -> str:
        return f"<ResultsNetwork(test_run_id='{self.test_run_id}', throughput_mbps={self.throughput_mbps})>"
```

You would also need to update the `TestRun` model to include the relationship:

```python
# Add this line to the TestRun class relationships section
results_network = relationship("ResultsNetwork", back_populates="test_run")
```

And update the `MODEL_REGISTRY`:

```python
MODEL_REGISTRY = {
    # ... existing models ...
    "results_network": ResultsNetwork,
}
```

For this example, we'll assume the generic JSON storage is sufficient, but the above shows how to create dedicated columns for better query performance.

### Step 6: Create Example Test Data

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

Create `examples/environments/network-lab.yaml`:

```yaml
name: "network-lab-01"
type: "lab"
comments: "Network performance testing lab environment"

tools:
  iperf3:
    version: "3.12"
    command: "iperf3"
    options:
      port: 5201
      parallel: 1
      time: 60

metadata:
  location: "Network Lab - Switch Rack 1"
  rack: "NET-LAB-R01"
  datacenter: "main-lab"
  environment_owner: "network-team"
  contact_email: "network-team@company.com"

  hardware:
    switch_model: "Cisco Catalyst 9300"
    switch_ports: "48x1GbE + 4x10GbE"
    server_nic: "Intel X550-T2"
    cable_type: "Cat6A"

  software:
    operating_system: "Ubuntu 22.04.3 LTS"
    kernel_version: "5.15.0-88-generic"
    iperf3_version: "3.12"

  network:
    test_subnet: "192.168.100.0/24"
    server_ip: "192.168.100.10"
    client_ip: "192.168.100.11"
    mtu: 1500

  tags:
    - "network"
    - "performance"
    - "lab"
    - "gigabit"
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

### Step 9: Create ZIP Generation Script

Create `examples/create_network_test_zip.sh`:

```bash
#!/bin/bash

echo "Creating network test ZIP package..."

# Create temporary directory
TEMP_DIR="temp_network_test"
ZIP_NAME="network_test_001.zip"

# Clean up any existing temp directory
rm -rf $TEMP_DIR
rm -f $ZIP_NAME

# Create directory structure
mkdir -p $TEMP_DIR

# Copy test results
cp test_results/network_run_001/network_results.csv $TEMP_DIR/

# Create ZIP
cd $TEMP_DIR
zip ../$ZIP_NAME *.csv
cd ..

# Clean up
rm -rf $TEMP_DIR

echo "✅ Created $ZIP_NAME"
echo "You can now import this with:"
echo "uv run benchmark-analyzer import-results \\"
echo "  --package $ZIP_NAME \\"
echo "  --type network \\"
echo "  --environment environments/network-lab.yaml \\"
echo "  --bom boms/network-server.yaml \\"
echo "  --engineer 'Network Team' \\"
echo "  --comments 'Network performance baseline test'"
```

Make the script executable:

```bash
chmod +x examples/create_network_test_zip.sh
```

### Step 10: Test the Implementation

1. **Initialize the database** (if not already done):
   ```bash
   uv run benchmark-analyzer db init
   ```

2. **Generate the test ZIP**:
   ```bash
   cd examples
   ./create_network_test_zip.sh
   ```

3. **Import the test data**:
   ```bash
   uv run benchmark-analyzer import-results \
     --package examples/network_test_001.zip \
     --type network \
     --environment examples/environments/network-lab.yaml \
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
   
   # List available test types
   uv run benchmark-analyzer query test-types
   ```

5. **Test the API** (if running):
   ```bash
   # Start the API
   uv run benchmark-api
   
   # In another terminal, test the endpoints
   curl http://localhost:8000/api/v1/test-types/
   curl http://localhost:8000/api/v1/test-runs/
   ```

## Validation and Testing

### Schema Validation
Test your schema with sample data:

```bash
uv run benchmark-analyzer schema validate \
  --schema benchmark_analyzer/contracts/tests/network/schema.json \
  --data examples/test_results/network_run_001/network_results.csv
```

### Parser Testing
Verify the parser can handle your test files:

```python
# Quick test in Python REPL
from benchmark_analyzer.core.parser import ParserRegistry
from pathlib import Path

parser = ParserRegistry.get_parser("network")
result = parser.parse_file(Path("examples/test_results/network_run_001/network_results.csv"))
print(result)
```

## Common Issues and Troubleshooting

1. **Schema Validation Errors**: Ensure your test data matches the schema exactly
2. **Parser Registration**: Make sure the parser is registered in the `ParserRegistry`
3. **Import Failures**: Check that all required fields are present in your test data
4. **Database Errors**: Verify database connection and table initialization

## Best Practices

1. **Keep schemas simple** but comprehensive enough to validate essential fields
2. **Use descriptive test names** that include the tool and test type
3. **Include timestamps** in ISO 8601 format for proper time-series analysis
4. **Add metadata** to provide context for test results
5. **Test with various data sizes** to ensure parser robustness
6. **Document any custom validation logic** in comments

## File Summary

After completing this guide, you should have created:

- `benchmark_analyzer/contracts/tests/network/schema.json`
- `benchmark_analyzer/contracts/tests/network/bom_schema.json` (optional)
- Parser code added to `benchmark_analyzer/core/parser.py`
- `examples/test_results/network_run_001/network_results.csv`
- `examples/environments/network-lab.yaml`
- `examples/boms/network-server.yaml`
- `examples/create_network_test_zip.sh`

Your new test type is now ready for use in the benchmark analyzer framework!