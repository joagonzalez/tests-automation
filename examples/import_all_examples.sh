#!/bin/bash

# Import All Example Data Script
# ==============================

set -e

echo "🚀 Starting import of all example benchmark data..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Load environment variables the same way as Makefile
if [ -f .env ]; then
    print_status "Loading environment variables from .env"
    set -a && . ./.env && set +a
fi

# Check if infrastructure is running
print_status "Checking if infrastructure is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status "API not running. Let's check database first..."
fi

# Test database connection
print_status "Testing database connection..."
if ! uv run benchmark-analyzer db status; then
    print_error "Database connection failed. Please ensure the infrastructure is running."
    print_status "Try: make dev-up"
    exit 1
fi

# Import Lab Server Results
print_status "Importing Lab Server CPU/Memory benchmark results..."
if uv run benchmark-analyzer import-results \
    --package examples/test_results/lab_server_benchmark_001.zip \
    --type cpu_mem \
    --environment examples/environments/lab-server-01.yaml \
    --bom examples/boms/standard-server.yaml \
    --engineer "Lab Team" \
    --comments "High-performance server baseline benchmark - Intel Xeon Gold 6230R"; then
    print_success "✓ CPU/Memory benchmark results imported successfully"
else
    print_error "Failed to import CPU/Memory benchmark results"
    exit 1
fi

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

# Show summary
print_status "Getting database summary..."
uv run benchmark-analyzer db status

print_status "Listing imported test runs..."
uv run benchmark-analyzer query test-runs --limit 10

print_success "✅ All example data imported successfully!"
print_status ""
print_status "📊 Summary of imported test types:"
print_status "  • cpu_mem: CPU and Memory performance benchmarks"
print_status "  • network_perf: Network performance benchmarks"
print_status ""
print_status "🌐 You can now:"
print_status "  • Visit API docs: http://localhost:8000/docs"
print_status "  • View Grafana: http://localhost:3000 (admin/admin123)"
print_status "  • Query data: uv run benchmark-analyzer query test-runs"
print_status "  • Query specific types: uv run benchmark-analyzer query test-runs --type cpu_mem"
print_status "  • Query specific types: uv run benchmark-analyzer query test-runs --type network_perf"
