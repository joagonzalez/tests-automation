# Network Performance Test Type Implementation

## Overview

This document describes the implementation of the new `network_perf` test type for the benchmark analyzer application. This test type enables comprehensive network performance testing and result storage alongside the existing `cpu_mem` test type.

## Implementation Summary

### 1. Database Model (`ResultsNetworkPerf`)

**File**: `tests-automation/benchmark_analyzer/db/models.py`

Added a new database model `ResultsNetworkPerf` with the following metrics:

#### Latency Metrics (milliseconds)
- `tcp_latency_avg_ms`, `tcp_latency_min_ms`, `tcp_latency_max_ms`
- `udp_latency_avg_ms`, `udp_latency_min_ms`, `udp_latency_max_ms`

#### Throughput Metrics (Mbps)
- `tcp_throughput_mbps`, `udp_throughput_mbps`
- `download_bandwidth_mbps`, `upload_bandwidth_mbps`

#### Connection & Quality Metrics
- `connection_establishment_time_ms`
- `connections_per_second`
- `packet_loss_percent`
- `jitter_ms`

#### Test Configuration
- `test_duration_sec`, `concurrent_connections`
- `packet_size_bytes`, `test_tool`

### 2. API Integration

**File**: `tests-automation/api/endpoints/results.py`

- Added `ResultsNetworkPerf` import
- Updated `RESULTS_TABLE_MAP` to include `'network_perf': ResultsNetworkPerf`
- Leverages existing dynamic test type handling

**File**: `tests-automation/api/services/database.py`

- Added `ResultsNetworkPerf` import for service layer compatibility

### 3. Data Loader Enhancement

**File**: `tests-automation/benchmark_analyzer/core/loader.py`

- Added `ResultsNetworkPerf` import
- Implemented `_load_network_perf_results()` method
- Implemented `_aggregate_network_perf_results()` helper method
- Updated test type routing to handle `network_perf`
- Added network performance results count to statistics

### 4. Example Data & Configuration

#### Test Results Package
**File**: `tests-automation/examples/test_results/lab_server_network_benchmark_001.zip`

Contains realistic network performance test data with:
- TCP/UDP latency measurements
- Throughput/bandwidth metrics
- Connection performance data
- Tool metadata (iperf3, netperf, ping)

#### Network Environment Configuration
**File**: `tests-automation/examples/environments/lab-server-network.yaml`

Specialized environment configuration featuring:
- Network testing tools (iperf3, netperf, ping, traceroute)
- Network-optimized hardware specifications
- Performance tuning parameters
- Network buffer configurations

#### Network-Optimized BOM
**File**: `tests-automation/examples/boms/network-server.yaml`

Hardware/software configuration optimized for network testing:
- Intel X710 10GbE network cards
- Network-specific kernel parameters
- Specialized network tools and drivers
- TCP/UDP stack optimizations

### 5. Load Testing Script Updates

**File**: `tests-automation/examples/import_all_examples.sh`

Enhanced the import script to:
- Import both `cpu_mem` and `network_perf` test types
- Improved error handling and status reporting
- Better user feedback and guidance

### 6. Documentation

**File**: `tests-automation/examples/test_results/NETWORK_PERFORMANCE_README.md`

Comprehensive documentation covering:
- JSON schema specification
- Usage examples and commands
- Integration details
- Best practices and supported tools

## Key Design Decisions

### 1. Extensible Architecture
- Maintained the existing `RESULTS_TABLE_MAP` pattern
- No changes to core API or CLI interfaces
- Easy addition of future test types

### 2. Comprehensive Metrics
- Covers major network performance aspects: latency, throughput, quality
- Supports multiple protocols (TCP/UDP)
- Includes test configuration for reproducibility

### 3. Tool Agnostic
- Flexible JSON schema supports various network testing tools
- Standardized metric names for consistency
- Metadata fields for tool-specific information

### 4. Production Ready
- Follows existing patterns and conventions
- Comprehensive error handling
- Thorough testing and validation

## Usage Examples

### Import Network Performance Results
```bash
uv run benchmark-analyzer import-results \
    --package examples/test_results/lab_server_network_benchmark_001.zip \
    --type network_perf \
    --environment examples/environments/lab-server-network.yaml \
    --bom examples/boms/network-server.yaml \
    --engineer "Network Team" \
    --comments "10GbE performance baseline"
```

### Query Results
```bash
# List network performance test runs
uv run benchmark-analyzer query test-runs --type network_perf

# Get all test runs
uv run benchmark-analyzer query test-runs
```

### API Access
```bash
# Get network performance results
curl "http://localhost:8000/api/v1/results/network_perf?limit=10"

# Get results statistics
curl "http://localhost:8000/api/v1/results/stats"
```

## Database Schema

The new `results_network_perf` table is automatically created via SQLAlchemy migrations when the application starts. It follows the same pattern as `results_cpu_mem` with a foreign key relationship to `test_runs`.

## Integration Points

### 1. Database Layer
- Automatic table creation via SQLAlchemy `Base.metadata.create_all()`
- Foreign key relationship to `test_runs` table
- Indexed on `test_run_id` for query performance

### 2. API Layer
- Dynamic test type routing via `RESULTS_TABLE_MAP`
- Consistent endpoint patterns across test types
- Automatic OpenAPI documentation generation

### 3. CLI Layer
- Leverages existing import/query commands
- No changes to user interface
- Transparent test type handling

### 4. Data Processing
- Parser-agnostic result loading
- Flexible JSON schema handling
- Extensible aggregation patterns

## Testing Approach

### 1. Model Validation
- Import testing for database models
- Table creation verification
- Model instantiation testing

### 2. Integration Testing
- End-to-end import process
- API endpoint functionality
- CLI command execution

### 3. Data Validation
- JSON schema compliance
- Database constraint validation
- Result aggregation accuracy

## Future Enhancements

### 1. Additional Test Types
The architecture supports easy addition of new test types:
- I/O performance (`io_perf`)
- GPU compute (`gpu_compute`)
- Storage benchmarks (`storage_perf`)

### 2. Advanced Analytics
- Statistical analysis across test types
- Performance trend analysis
- Automated regression detection

### 3. Enhanced Visualizations
- Grafana dashboard templates
- Network topology visualization
- Performance correlation analysis

## Maintenance

### Adding New Test Types
1. Create new `Results*` model in `models.py`
2. Add to `RESULTS_TABLE_MAP` in `results.py`
3. Implement loader method in `loader.py`
4. Create example data and configuration
5. Update documentation

### Schema Evolution
- Database schema changes handled via SQLAlchemy
- Backward compatibility maintained
- Migration strategies documented

## Conclusion

The network performance test type implementation successfully extends the benchmark analyzer application with comprehensive network testing capabilities while maintaining architectural consistency and ease of use. The implementation follows established patterns and provides a clear template for future test type additions.