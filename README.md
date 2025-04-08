# 🔧 Benchmark Analyzer

A modular CLI application for processing and analyzing hardware/software test results. The tool handles test results in JSON/CSV formats, validates them against schemas, stores them in a SQLite database, and provides visualization through Streamlit dashboards.

## 📋 Features

- Import and process test result packages (ZIP files)
- Schema validation for test results
- Environment and BOM (Bill of Materials) management
- SQLite database storage
- Interactive Streamlit dashboards
- Support for multiple test types
- Flexible parser system

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/benchmark-analyzer.git
cd benchmark-analyzer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Basic Usage

1. Import test results:
```bash
python cli.py import \
  --package test_data/memory_results.zip \
  --type memory_bandwidth \
  --environment contracts/environments/env1.yaml \
  --bom contracts/tests/memory_bandwidth/bom.yaml
```

2. Launch dashboard:
```bash
streamlit run benchmark_analyzer/dashboards/streamlit_app.py
```

## 🧩 Adding New Test Types

### 1. Create Directory Structure

```bash
benchmark_analyzer/contracts/tests/new_test_type/
├── schema.json       # Test result schema
├── bom.yaml         # Hardware/software specifications
└── bom_schema.json  # BOM validation schema
```

### 2. Define Schema

Create `schema.json`:
```json
{
  "type": "object",
  "properties": {
    "test_name": {"type": "string"},
    "metric_1": {"type": "number"},
    "metric_2": {"type": "number"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "required": ["test_name", "metric_1", "timestamp"]
}
```

### 3. Create Parser

Add new parser in `core/parser.py`:
```python
class NewTestTypeParser(BaseParser):
    """Parser for new test type results."""

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path) as f:
            # Add parsing logic here
            data = json.load(f)  # or csv.DictReader(f)
            return {
                "test_name": data["test_name"],
                "metric_1": float(data["metric_1"]),
                "timestamp": data["timestamp"]
            }

    def _is_valid_result_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".json"  # or .csv

# Register parser
ParserRegistry._parsers["new_test_type"] = NewTestTypeParser
```

### 4. Add Database Model

In `db/models.py`:
```python
class ResultsNewTestType(Base):
    """Model for new test type results."""
    __tablename__ = "results_new_test_type"

    result_id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.test_run_id"))
    test_name = Column(String)
    metric_1 = Column(Float)
    metric_2 = Column(Float)
    timestamp = Column(DateTime)
```

### 5. Update Dashboard

Add visualization support in `dashboards/streamlit_app.py`:
```python
elif test_type == "new_test_type":
    results_df = load_new_test_type_results(session, filtered_runs['test_run_id'].tolist())
    # Add visualization code
```

## 🌍 Adding New Environments

1. Create environment YAML file:
```bash
# contracts/environments/new_env.yaml
name: "new_environment"
type: "production"
comments: "New environment description"
tools:
  tool1: "1.0.0"
  tool2: "2.1.0"
metadata:
  location: "datacenter-2"
  rack: "R15"
```

2. Environment will be automatically registered when used in imports

## 📦 Adding New BOMs

1. Create BOM YAML file:
```bash
# contracts/tests/test_type/bom.yaml
hardware:
  name: "server-config-x"
  version: "1.0"
  specs:
    cpu: "Intel Xeon Gold 6230R"
    ram: "128GB DDR4-3200"

software:
  name: "benchmark-suite-x"
  version: "2.0.0"
  specs:
    os: "Ubuntu 22.04 LTS"
    kernel: "5.15.0-88-generic"
```

2. BOM will be validated and registered during test import

## 📊 Database Schema

Key tables:
- `test_runs`: Test execution metadata
- `results_*`: Test type specific results
- `environments`: Environment definitions
- `hw_bom`/`sw_bom`: Hardware/software specifications

## 🛠️ Development

### Running Tests
```bash
pytest
```