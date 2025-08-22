# Network Performance Test Type

This directory contains example data for the `network_perf` test type, which measures network performance characteristics including latency, throughput, and connection metrics.

## Overview

The network performance test type (`network_perf`) is designed to capture comprehensive network benchmarking results from tools like iperf3, netperf, and ping. It stores results in the `results_network_perf` database table.

## Test Data Structure

### Example Package: `lab_server_network_benchmark_001.zip`

This package contains:
- `network_lab_run_001/network_perf_results.json` - Network performance test results

### JSON Schema

The network performance results JSON file should contain the following fields:

#### Required Fields
- `test_name`: String identifier for the test
- `timestamp`: ISO 8601 timestamp of when the test was run
- `test_duration_sec`: Duration of the test in seconds

#### Latency Metrics (in milliseconds)
- `tcp_latency_avg_ms`: Average TCP latency
- `tcp_latency_min_ms`: Minimum TCP latency
- `tcp_latency_max_ms`: Maximum TCP latency
- `udp_latency_avg_ms`: Average UDP latency
- `udp_latency_min_ms`: Minimum UDP latency
- `udp_latency_max_ms`: Maximum UDP latency

#### Throughput Metrics (in Mbps)
- `tcp_throughput_mbps`: TCP throughput
- `udp_throughput_mbps`: UDP throughput
- `download_bandwidth_mbps`: Download bandwidth
- `upload_bandwidth_mbps`: Upload bandwidth

#### Connection Metrics
- `connection_establishment_time_ms`: Time to establish connections
- `connections_per_second`: Connection rate
- `packet_loss_percent`: Packet loss percentage
- `jitter_ms`: Network jitter in milliseconds

#### Test Configuration
- `concurrent_connections`: Number of concurrent connections used
- `packet_size_bytes`: Packet size in bytes
- `test_tool`: Tool used for testing (e.g., "iperf3", "netperf")

#### Optional Fields
- `test_parameters`: Object containing test-specific parameters
- `error_count`: Number of errors encountered
- `warnings`: Array of warning messages
- `detailed_metrics`: Object with detailed per-protocol metrics
- `metadata`: Object with environment and tool information

## Usage

### Importing Network Performance Results

```bash
uv run benchmark-analyzer import-results \
    --package examples/test_results/lab_server_network_benchmark_001.zip \
    --type network_perf \
    --environment examples/environments/lab-server-network.yaml \
    --bom examples/boms/network-server.yaml \
    --engineer "Network Team" \
    --comments "High-performance network benchmark"
```

### Querying Results

```bash
# List test runs
uv run benchmark-analyzer query test-runs --type network_perf

# Get database statistics
uv run benchmark-analyzer db status
```

### API Access

```bash
# Get network performance results via API
curl "http://localhost:8000/api/v1/results/network_perf?limit=10"

# Get specific test run results
curl "http://localhost:8000/api/v1/results/network_perf/by-test-run/{test_run_id}"
```

## Supporting Files

### Environment Configuration

The network performance tests use a specialized environment configuration:
- **File**: `examples/environments/lab-server-network.yaml`
- **Features**: Network-optimized settings, iperf3/netperf tools, performance tuning

### BOM Configuration

The network performance tests use a network-optimized BOM:
- **File**: `examples/boms/network-server.yaml`
- **Features**: High-performance network cards (Intel X710), optimized kernel parameters

## Database Schema

The network performance results are stored in the `results_network_perf` table with the following key columns:

- `test_run_id` (Primary Key): Links to the test run
- Latency metrics: `tcp_latency_*`, `udp_latency_*`
- Throughput metrics: `*_throughput_mbps`, `*_bandwidth_mbps`
- Quality metrics: `packet_loss_percent`, `jitter_ms`
- Connection metrics: `connection_establishment_time_ms`, `connections_per_second`
- Test configuration: `test_duration_sec`, `concurrent_connections`, etc.

## Best Practices

1. **Consistent Units**: Use milliseconds for latency, Mbps for throughput
2. **Tool Specification**: Always specify the `test_tool` used
3. **Comprehensive Testing**: Include both TCP and UDP metrics when possible
4. **Environment Documentation**: Use detailed environment and BOM configurations
5. **Metadata**: Include relevant tool versions and system information

## Supported Tools

The network performance test type is designed to work with:
- **iperf3**: TCP/UDP throughput and latency testing
- **netperf**: Various network performance tests
- **ping**: Basic latency measurements
- **hping3**: Advanced packet testing
- **Custom tools**: Any tool that produces compatible JSON output

## Example Commands

### iperf3 Testing
```bash
# TCP throughput test
iperf3 -c server_ip -t 60 -P 10 -J

# UDP throughput test  
iperf3 -c server_ip -u -b 1G -t 60 -J

# Latency test with small packets
iperf3 -c server_ip -t 60 -l 64 -J
```

### netperf Testing
```bash
# TCP stream test
netperf -H server_ip -t TCP_STREAM -l 60

# UDP request/response test
netperf -H server_ip -t UDP_RR -l 60
```

## Integration

This test type integrates with:
- **Database**: Stores results in `results_network_perf` table
- **API**: Available via `/api/v1/results/network_perf` endpoints
- **CLI**: Import and query via `benchmark-analyzer` commands
- **Grafana**: Visualizable through database connections