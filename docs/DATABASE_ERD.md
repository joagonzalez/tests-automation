# Database Entity Relationship Diagram (ERD)

This document describes the current database schema for the Benchmark Analyzer Framework, including entity relationships, design decisions, and architectural patterns.

## Overview

The database follows a star schema pattern with `test_runs` as the central fact table, surrounded by dimension tables for test metadata and specialized results tables for different test types.

## Core Entities

### Central Fact Table

#### test_runs
**Purpose**: Central fact table linking all test execution metadata
```sql
test_run_id      CHAR(36)     PRIMARY KEY
test_type_id     CHAR(36)     FOREIGN KEY → test_types.test_type_id
environment_id   CHAR(36)     FOREIGN KEY → environments.id (OPTIONAL)
hw_bom_id        CHAR(36)     FOREIGN KEY → hw_bom.bom_id (OPTIONAL)
sw_bom_id        CHAR(36)     FOREIGN KEY → sw_bom.bom_id (OPTIONAL)
created_at       TIMESTAMP    NOT NULL, INDEXED
engineer         VARCHAR(64)
comments         TEXT
configuration    JSON
```

**Design Notes**:
- UUID-based primary key for global uniqueness
- Optional foreign keys provide flexibility for minimal test runs
- JSON configuration field for extensible metadata
- Indexed timestamp for time-based queries

### Dimension Tables

#### test_types
**Purpose**: Defines available test types (e.g., 'cpu_mem', 'network_perf')
```sql
test_type_id     CHAR(36)     PRIMARY KEY
name             VARCHAR(64)  UNIQUE, NOT NULL
description      TEXT
```

#### environments
**Purpose**: Test environment configurations
```sql
id               CHAR(36)     PRIMARY KEY
name             VARCHAR(128)
type             VARCHAR(32)  (e.g., 'cloud', 'bare-metal', 'vm')
comments         TEXT
tools            JSON         Tool versions and configurations
env_metadata     JSON         Additional environment data
```

#### hw_bom (Hardware Bill of Materials)
**Purpose**: Hardware configuration specifications with deduplication
```sql
bom_id           CHAR(36)     PRIMARY KEY
specs            JSON         NOT NULL, Hardware specifications
specs_hash       VARCHAR(64)  UNIQUE, SHA256 hash for deduplication
```

#### sw_bom (Software Bill of Materials)
**Purpose**: Software configuration specifications with deduplication
```sql
bom_id           CHAR(36)     PRIMARY KEY
specs            JSON         NOT NULL, Software specifications
specs_hash       VARCHAR(64)  UNIQUE, SHA256 hash for deduplication
kernel_version   VARCHAR(50)  GENERATED COLUMN, extracted from JSON, INDEXED
```

### Results Tables

The system uses a **one-table-per-test-type-family** approach for storing test results.

#### results_cpu_mem
**Purpose**: CPU and Memory benchmark results
```sql
test_run_id                          CHAR(36)  PRIMARY KEY, FOREIGN KEY CASCADE DELETE
-- Memory Metrics
memory_idle_latency_ns               DOUBLE
memory_peak_injection_bandwidth_mbs  DOUBLE
ramspeed_smp_bandwidth_mbs_add       DOUBLE
ramspeed_smp_bandwidth_mbs_copy      DOUBLE
sysbench_ram_memory_bandwidth_mibs   INT
sysbench_ram_memory_test_duration_sec INT
sysbench_ram_memory_test_mode        VARCHAR(8)
-- CPU Metrics
sysbench_cpu_events_per_second       INT
sysbench_cpu_duration_sec            INT
sysbench_cpu_test_mode               VARCHAR(16)
```

#### results_network_perf
**Purpose**: Network performance benchmark results
```sql
test_run_id                      CHAR(36)  PRIMARY KEY, FOREIGN KEY CASCADE DELETE
-- Latency Metrics (milliseconds)
tcp_latency_avg_ms               DOUBLE
tcp_latency_min_ms               DOUBLE
tcp_latency_max_ms               DOUBLE
udp_latency_avg_ms               DOUBLE
udp_latency_min_ms               DOUBLE
udp_latency_max_ms               DOUBLE
-- Throughput Metrics (Mbps)
tcp_throughput_mbps              DOUBLE
udp_throughput_mbps              DOUBLE
download_bandwidth_mbps          DOUBLE
upload_bandwidth_mbps            DOUBLE
-- Connection & Quality Metrics
connection_establishment_time_ms DOUBLE
connections_per_second           INT
packet_loss_percent              DOUBLE
jitter_ms                        DOUBLE
-- Test Configuration
test_duration_sec                INT
concurrent_connections           INT
packet_size_bytes                INT
test_tool                        VARCHAR(32)
```

### Support Tables

#### acceptance_criteria
**Purpose**: Define test acceptance thresholds and validation rules
```sql
id               CHAR(36)     PRIMARY KEY
test_type_id     CHAR(36)     FOREIGN KEY → test_types.test_type_id
metric           VARCHAR(64)  NOT NULL, Metric name to evaluate
op_id            TINYINT      FOREIGN KEY → operators.op_id
threshold_min    DOUBLE       Minimum threshold value
threshold_max    DOUBLE       Maximum threshold value
target_component VARCHAR(32)  Component target (cpu, memory, network, etc.)
```

#### operators
**Purpose**: Lookup table for comparison operators
```sql
op_id            TINYINT      PRIMARY KEY
code             VARCHAR(8)   UNIQUE, Operator code (lt, lte, eq, neq, gt, gte, btw)
description      VARCHAR(64)  Human-readable description
```

### Views

#### v_test_runs_summary
**Purpose**: Denormalized view for fast reporting queries
```sql
test_run_id      CHAR(36)
test_type_id     CHAR(36)
environment_id   CHAR(36)
hw_bom_id        CHAR(36)
sw_bom_id        CHAR(36)
created_at       TIMESTAMP
engineer         VARCHAR(64)
comments         TEXT
configuration    JSON
kernel_version   VARCHAR(50)  Extracted from sw_bom
test_name        VARCHAR(64)  Extracted from test_types
```

## Relationships

### Primary Relationships

1. **test_types → test_runs** (1:N)
   - Each test type can have multiple test executions
   - Mandatory relationship

2. **environments → test_runs** (1:N, Optional)
   - Tests can optionally specify environment
   - Allows for environment-less testing

3. **hw_bom → test_runs** (1:N, Optional)
   - Hardware configuration optionally linked
   - Supports testing without hardware specifications

4. **sw_bom → test_runs** (1:N, Optional)
   - Software configuration optionally linked
   - Enables minimal test runs without software details

5. **test_runs → results_* tables** (1:0..1)
   - Each test run can have results in exactly one results table
   - Results tables are mutually exclusive
   - Cascade delete maintains referential integrity

6. **test_types → acceptance_criteria** (1:N)
   - Each test type can have multiple acceptance criteria
   - Flexible validation system

7. **operators → acceptance_criteria** (1:N)
   - Reusable comparison operators
   - Supports range and single-value comparisons

## Design Patterns

### 1. Star Schema
- `test_runs` as central fact table
- Dimension tables for context and metadata
- Optimized for analytical queries

### 2. Optional Foreign Keys
- Non-mandatory relationships for flexibility
- Supports minimal test configurations
- Gradual schema adoption

### 3. Hash-Based Deduplication
- BOM tables use SHA256 hash of specs
- Prevents duplicate configurations
- Enables efficient comparison

### 4. JSON Extensibility
- Configuration and specification fields use JSON
- Schema evolution without migrations
- Flexible metadata storage

### 5. Generated Columns
- `kernel_version` extracted from `sw_bom.specs`
- Indexed for performance
- Additional extractions can be added

### 6. Cascade Delete
- Results tables cascade delete with test_runs
- Maintains referential integrity
- Simplifies cleanup operations

## Indexing Strategy

### Primary Indexes
- All primary keys (UUID-based)
- Foreign key columns for join performance

### Performance Indexes
- `test_runs.created_at` - Time-based queries
- `sw_bom.kernel_version` - Kernel-specific filtering
- `acceptance_criteria(test_type_id, metric)` - Criteria lookups

### Unique Constraints
- `test_types.name` - Prevent duplicate test type names
- `operators.code` - Unique operator codes
- `hw_bom.specs_hash` - Hardware deduplication
- `sw_bom.specs_hash` - Software deduplication

## Query Patterns

### Common Queries

1. **Test Run Summary**
```sql
SELECT tr.test_run_id, tt.name, tr.created_at, tr.engineer
FROM test_runs tr
JOIN test_types tt ON tr.test_type_id = tt.test_type_id
ORDER BY tr.created_at DESC;
```

2. **Results with Environment**
```sql
SELECT tr.test_run_id, env.name, rcm.sysbench_cpu_events_per_second
FROM test_runs tr
LEFT JOIN environments env ON tr.environment_id = env.id
LEFT JOIN results_cpu_mem rcm ON tr.test_run_id = rcm.test_run_id
WHERE tt.name = 'cpu_mem';
```

3. **Hardware Configuration Analysis**
```sql
SELECT hw.specs->>'$.cpu.model', COUNT(*) as test_count
FROM test_runs tr
JOIN hw_bom hw ON tr.hw_bom_id = hw.bom_id
GROUP BY hw.specs->>'$.cpu.model';
```

## Scaling Considerations

### Partitioning Strategy
- Consider partitioning `test_runs` by date
- Results tables can be partitioned by test_run_id ranges
- Archive old test data to separate tables

### Performance Optimization
- Materialized views for complex aggregations
- Read replicas for reporting workloads
- Result table-specific indexes based on query patterns

### Schema Evolution
- JSON fields allow schema changes without migrations
- New result tables can be added without affecting existing data
- Generated columns provide performance without breaking changes

## Migration Path

### Adding New Test Types
1. Insert into `test_types` table
2. Create new `results_<test_type>` table
3. Update application to route to new table
4. Add acceptance criteria as needed

### BOM Schema Changes
- Modify JSON structure in new records
- Old records remain valid
- Use JSON queries to handle version differences
- Consider migration scripts for major changes

## Data Integrity

### Constraints
- Foreign key constraints with appropriate cascade rules
- JSON validation constraints on JSON fields
- Check constraints for business rules

### Validation
- Application-level validation before database insert
- Schema validation for JSON fields
- Acceptance criteria validation post-insert

### Backup Strategy
- Regular full database backups
- Point-in-time recovery capability
- Test data archival for long-term storage

---

*This ERD documentation reflects the current database schema. Update this document when making schema changes.*