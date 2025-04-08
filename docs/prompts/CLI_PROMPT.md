
# 🔧 CLI App Prompt for Claude — Benchmark Analyzer

## 🧠 Context

We’re developing a **modular CLI application** called `benchmark-analyzer`. The goal is to process and analyze hardware/software test results generated from benchmarking tools. These results are saved as JSON or CSV files and packaged as `.zip` files. The CLI extracts data, validates it against provided schemas, stores it in a local SQLite database, and optionally visualizes it through Streamlit dashboards.

The application will be used by two main personas:
- **Test Operator**: Executes tests, prepares result packages.
- **Test Analyst**: Imports, analyzes results, and creates reports.

---

## 📁 File Inputs

The CLI will work with these inputs:

- `.zip` file of raw test data:
  Contains files like `raw_test_data_1.json`, `raw_test_data_2.csv`, etc.

- Environment definition:
  `contracts/environments/env1/environment.yaml`
  + `contracts/environments/env1/schema.json`

- Test type definition:
  `contracts/tests/test_1/schema.json`
  + `contracts/tests/test_1/bom.yaml`
  + `contracts/tests/test_1/bom_schema.json`

- Result file:
  `results/results_1.csv`

---

## ⚙️ CLI Commands (based on user sequence)

**Example CLI usage:**

```bash
benchmark-analyzer import \
  --package test_results_<date>.zip \
  --type <test_type> \
  --bom <bom_file>.yaml \
  --environment <environment_name>.yaml
```

### CLI Workflow

1. Load and validate the input result using its associated schema.
2. Validate/create:
   - BOM using `bom_schema`
   - Environment using `environment schema`
   - Test type using `test schema`
3. Insert:
   - Test run metadata
   - Raw test results into specific `results_test_type_N` table
4. Store metadata, tools used, config, etc.
5. Enable SQL query/criteria filtering
6. Trigger optional dashboard visualization

---

## 🗃️ Data Model (from DER)

### Table: `test_runs`
- `test_run_id` (PK), `test_type_id` (FK), `environment_id` (FK)
- `hw_bom_id`, `sw_bom_id` (FKs)
- `created_at`, `engineer`, `comments`, `configuration (JSON)`

### Table: `results_test_type_1`
- `test_type_id` (PK), `test_type` (TEXT)
- Metrics: `memory_idle_latency_ns`, `sysbench_cpu_duration_sec`, etc.

### Table: `hw_bom` / `sw_bom`
- `bom_id` (PK)
- `specs (JSON)`

### Table: `environment`
- `environment_id` (PK)
- `name`, `type`, `comments`, `tools (JSON)`, `metadata (JSON)`

### Table: `acceptance_criteria`
- `criteria_id`, `test_type_id` (FK), `metric`
- `threshold`, `operator`, `target_component`

---

## 🧱 Architecture and Modules (from architecture diagram)

### CLI Modules

- **unzipping** the `.zip` file
- **parsing** each result file
- **querying** an Engineering SOR API for external metadata
- **loading** validated data into SQLite/PostgreSQL
- **exporting** or visualizing results using Streamlit

### Architecture Stack

- Language: **Python**
- CLI: **Typer**
- DB: **SQLite (or PostgreSQL)**
- Validation: **JSON Schema**
- Visualization: **Streamlit Dashboards**

---

## 📁 Suggested Code Structure (from app structure)

```
benchmark-analyzer/
├── cli/                     # CLI entrypoints via Typer
│   └── main.py              # Main CLI interface
├── core/
│   ├── parser.py            # Input file parser and adapter
│   ├── loader.py            # DB insertion and metadata manager
│   ├── validator.py         # Schema validators
│   └── criteria.py          # Acceptance criteria checks
├── db/
│   ├── models.py            # SQLAlchemy/DDL models
│   └── connector.py         # DB session manager
├── services/
│   └── sor_client.py        # Engineering SOR API interface
├── dashboards/
│   └── streamlit_app.py     # Dashboards for results
└── contracts/               # Environment/test definitions
    ├── environments/
    └── tests/
```

---

## ✅ Example SQL Query for Acceptance Criteria

```sql
SELECT *
FROM results_test_type_1 r
JOIN acceptance_criteria a ON a.metric = 'sysbench_cpu_duration_sec'
WHERE r.sysbench_cpu_duration_sec > CAST(a.threshold AS INTEGER)
  AND a.operator = '>';
```

---

## ✨ Task for Claude

**Generate:**
- A skeleton Python CLI app using **Typer**, **SQLite**, and **JSON Schema validation**.
- Classes/modules for parsing, validation, database loading, and criteria checks.
- CLI entrypoints and help messages.
- Include one example of a Streamlit dashboard module to display results from the DB.
- Structure the code to follow the architecture and file organization above.

---

## 🧩 Additional Requirements

### 1. Object-Oriented Design
- The codebase should follow **OOP principles** wherever possible.
- Use Python **typing annotations** to improve code clarity and type safety.
- Include **docstrings** for all classes and functions using a consistent format (e.g., Google or NumPy style).

### 2. Flexible Parser System
- Each **test type** will have its own **parser module**, responsible for:
  - Parsing the input file format for that specific test.
  - Producing a **YAML-compatible structure** that the CLI can load into the database.
- The CLI must support **easily adding new test types** with minimal code changes.
- Implement a **base parser class** and derive new parsers for each test type using polymorphism.
- Register parsers dynamically (e.g., via plugin registry or class mapping).

### 3. BOMs and Environments
- BOMs (Bill of Materials) and Environments will be provided as **YAML files**.
- Implement loaders and schema validators for:
  - `contracts/tests/<test_type>/bom.yaml`
  - `contracts/environments/<env_name>/environment.yaml`
- YAML input should be validated against their corresponding schema (`bom_schema.json`, `environment_schema.json`).


---

## 🧪 Test Types, Parsers, and Schema Validation

### Parser Behavior
- Each **test type** must be associated with a **schema definition** (`schema.json`).
- A **dedicated parser** will:
  1. Parse the test result format (e.g., JSON, CSV).
  2. Convert it into a **YAML-compatible dictionary**.
  3. Validate this dictionary against the test type's **JSON schema**.

### Parser Design
- Use an **abstract base class** (e.g., `BaseParser`) to define the interface.
- Each test type implements its own parser that extends `BaseParser`.
- Parsers should be **auto-discoverable** or easily pluggable via a registry or factory pattern.

---

## 🧪 Example Test Types and Parsers

### Test Type 1: `memory_bandwidth`

#### Input Format (CSV)
```csv
test_name,read_bw,write_bw,timestamp
memtest1,2300,2100,2024-03-01T15:23:00
```

#### Schema (`contracts/tests/memory_bandwidth/schema.json`)
```json
{
  "type": "object",
  "properties": {
    "test_name": {"type": "string"},
    "read_bw": {"type": "number"},
    "write_bw": {"type": "number"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "required": ["test_name", "read_bw", "write_bw", "timestamp"]
}
```

#### Parser Output (YAML-compatible)
```yaml
test_name: memtest1
read_bw: 2300
write_bw: 2100
timestamp: "2024-03-01T15:23:00"
```

---

### Test Type 2: `cpu_latency`

#### Input Format (JSON)
```json
{
  "latencies_ns": [102, 110, 98, 107],
  "average_ns": 104.25,
  "test_name": "latency_test",
  "timestamp": "2024-03-01T16:00:00"
}
```

#### Schema (`contracts/tests/cpu_latency/schema.json`)
```json
{
  "type": "object",
  "properties": {
    "test_name": {"type": "string"},
    "latencies_ns": {
      "type": "array",
      "items": {"type": "integer"}
    },
    "average_ns": {"type": "number"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "required": ["test_name", "latencies_ns", "average_ns", "timestamp"]
}
```

#### Parser Output (YAML-compatible)
```yaml
test_name: latency_test
latencies_ns:
  - 102
  - 110
  - 98
  - 107
average_ns: 104.25
timestamp: "2024-03-01T16:00:00"
```

---

### CLI E2E Behavior for Each Test Type
- On running:
  ```bash
  benchmark-analyzer import \
    --package memory_test_202403.zip \
    --type memory_bandwidth \
    --environment env1.yaml
  ```
- The app:
  1. Unpacks the zip file.
  2. Identifies the parser class for `memory_bandwidth`.
  3. Parser parses and produces structured YAML.
  4. CLI validates YAML against schema.
  5. Data is inserted into the SQLite DB under the appropriate table.

The same workflow applies for `cpu_latency` or any future test type.
