# Benchmark Analyzer

A CLI tool for importing, analyzing, and visualizing infrastructure benchmark results. This tool is designed to work with various types of benchmark tests, with initial support for CPU/Memory benchmarks.

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd benchmark-analyzer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Importing Test Results

```bash
# Import results from a ZIP file with YAML
python -m src.main import-results \
    artifacts/test_results.yaml \
    --environment artifacts/environment.yaml
```

### Listing Results

```bash
# List all recent results
python -m src.main list-results \
    --environment artifacts/environment.yaml

# List specific metrics for a test type
python -m src.main list-results \
    --environment artifacts/environment.yaml \
    --test-type cpu_memory_benchmark \
    --metrics memory.latency cpu.events_per_sec

# List available metrics for a test type
python -m src.main list-metrics cpu_memory_benchmark
```

### Launching Dashboard

```bash
# Run with default settings
python -m src.main dashboard

# Run on a specific port
python -m src.main dashboard --port 8502

# Run with a specific database
python -m src.main dashboard --db-path artifacts/benchmark_results.db
```

## Adding New Test Types

To add support for a new test type, you need to:

1. Create Schema Files:
   - Add a new JSON schema in `schemas/` directory
   - Add corresponding Python schema in `src/schemas/`

Example schema structure:
```python
# src/schemas/new_test_type_schema.py
SCHEMA = {
    "type": "object",
    "required": ["metadata", "benchmark_results"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["test_id", "timestamp", "test_type", "environment"],
            "properties": {
                "test_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "test_type": {"type": "string"},
                "environment": {"type": "string"}
            }
        },
        "benchmark_results": {
            "type": "object",
            "required": ["metric_1", "metric_2"],
            "properties": {
                "metric_1": {
                    "type": "number",
                    "description": "Description of metric 1"
                },
                "metric_2": {
                    "type": "object",
                    "properties": {
                        "sub_metric_1": {"type": "number"},
                        "sub_metric_2": {"type": "string"}
                    }
                }
            }
        }
    }
}
```

2. Create YAML Test Results Template:
   - Create a template in `artifacts/` showing the expected format

Example test results YAML:
```yaml
metadata:
  test_id: new_test_001
  timestamp: "2024-02-20T14:30:00Z"
  test_type: "new_test_type"
  environment: "prod_cluster_a"

benchmark_results:
  metric_1: 123.45
  metric_2:
    sub_metric_1: 67.89
    sub_metric_2: "some_value"
```

3. Update Dashboard (Optional):
   - Add new visualizations in `src/dashboard/main.py`
   - Add new queries in `src/dashboard/queries.py`

Example dashboard addition:
```python
# In src/dashboard/main.py
def plot_new_metric(df: pd.DataFrame):
    st.title("New Metric Visualization")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['metric_1'],
            mode='lines+markers',
            name='Metric 1'
        )
    )
    st.plotly_chart(fig)
```

## Project Structure

```
benchmark-analyzer/
├── artifacts/                 # Test results and environment configs
├── schemas/                   # JSON schemas for test validation
├── src/
│   ├── cli.py                # CLI implementation
│   ├── dashboard/            # Streamlit dashboard
│   ├── database/             # Database management
│   ├── schemas/              # Python schema definitions
│   └── utils/                # Utilities and helpers
├── tests/                    # Test cases
├── requirements.txt          # Dependencies
└── README.md                # This file
```

## Development

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
make test
```

3. Run linting:
```bash
make lint
```

4. Format code:
```bash
make format
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request