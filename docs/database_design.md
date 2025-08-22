# Database Design Documentation - Benchmark Analyzer

## Overview

The benchmark-analyzer application uses a MySQL database to store performance test results, hardware/software configurations, and acceptance criteria. The database follows a dimensional modeling approach with fact and dimension tables to support efficient analytics and reporting.

## Database Schema

### Core Tables

#### 1. Lookup Tables

**`operators`**
- Stores comparison operators for acceptance criteria (lt, lte, eq, neq, gt, gte, btw)
- Small reference table with predefined values
- Used by acceptance criteria to define threshold comparisons

**`test_types`**
- Defines available test types (e.g., 'cpu_latency', 'memory_bandwidth')
- UUID primary key with unique name constraint
- Extensible design allows adding new test types without schema changes

#### 2. Dimension Tables

**`environments`**
- Test environment configurations (cloud, bare-metal, vm)
- JSON fields for tools and metadata provide flexibility
- Captures toolchain versions and environment-specific information

**`hw_bom`** (Hardware Bill of Materials)
- Hardware specifications stored as JSON
- CPU, memory, storage, network, power configurations
- **Issue**: Currently generates new UUID for identical hardware specs

**`sw_bom`** (Software Bill of Materials)
- Software specifications stored as JSON
- OS, kernel, libraries, compiler versions
- Generated column `kernel_version` for fast filtering
- **Issue**: Currently generates new UUID for identical software specs

#### 3. Fact Table

**`test_runs`**
- Central fact table linking all dimensions
- Foreign keys to test_type, environment, hw_bom, sw_bom
- Captures test execution metadata, engineer, comments, configuration
- Timestamp for temporal analysis

#### 4. Results Tables

**`results_cpu_mem`**
- CPU and memory benchmark results
- One-to-one relationship with test_runs
- Separate tables planned for different test families (IO, network, etc.)
- Metrics include latency, bandwidth, duration, and mode information

#### 5. Acceptance Criteria

**`acceptance_criteria`**
- Defines pass/fail thresholds for test metrics
- Links test types with specific metric thresholds
- Supports range and single-value comparisons
- Component-specific criteria (cpu, memory, disk, network)

#### 6. Views

**`v_test_runs_summary`**
- Denormalized view combining test runs with related dimensions
- Includes kernel version and test type name for easy reporting
- Optimized for dashboard and reporting queries

## BOM Deduplication Issue

### Problem Description

The current implementation generates new UUIDs for BOMs every time, even when hardware/software specifications are identical. This leads to:

1. **Data Duplication**: Same hardware configuration stored multiple times
2. **Analytics Complexity**: Requires complex deduplication in queries
3. **Storage Waste**: Unnecessary storage overhead
4. **Reporting Inconsistency**: Same configurations appear as different entities

### Example of the Issue

```sql
-- Two identical hardware configurations with different IDs
SELECT bom_id, JSON_EXTRACT(specs, '$.cpu.model') as cpu_model 
FROM hw_bom 
WHERE JSON_EXTRACT(specs, '$.cpu.model') = 'Intel Xeon Gold 6230R';

-- Results:
-- 2343fc84-975a-41da-b39d-4661f8d61844 | Intel Xeon Gold 6230R
-- 51764514-8712-4d3b-8f9c-74170b475a9b | Intel Xeon Gold 6230R
```

### Proposed Solution: Hash-Based IDs

#### Implementation Strategy

1. **Add Hash Column**
```sql
ALTER TABLE hw_bom ADD COLUMN specs_hash VARCHAR(64) UNIQUE;
ALTER TABLE sw_bom ADD COLUMN specs_hash VARCHAR(64) UNIQUE;
CREATE INDEX idx_hw_bom_hash ON hw_bom(specs_hash);
CREATE INDEX idx_sw_bom_hash ON sw_bom(specs_hash);
```

2. **Modify BOM Creation Logic**
```python
import hashlib
import json

def create_or_get_hw_bom(specs: dict) -> str:
    """Create or retrieve existing hardware BOM based on specs hash."""
    # Create deterministic hash of specs
    specs_json = json.dumps(specs, sort_keys=True, separators=(',', ':'))
    specs_hash = hashlib.sha256(specs_json.encode()).hexdigest()
    
    # Check if BOM already exists
    existing_bom = session.query(HardwareBOM).filter_by(
        specs_hash=specs_hash
    ).first()
    
    if existing_bom:
        return existing_bom.bom_id
    
    # Create new BOM
    bom_id = str(uuid.uuid4())
    new_bom = HardwareBOM(
        bom_id=bom_id,
        specs=specs,
        specs_hash=specs_hash
    )
    session.add(new_bom)
    return bom_id
```

3. **Migration Process**
```sql
-- Step 1: Calculate hashes for existing records
UPDATE hw_bom SET specs_hash = SHA2(JSON_UNQUOTE(specs), 256);
UPDATE sw_bom SET specs_hash = SHA2(JSON_UNQUOTE(specs), 256);

-- Step 2: Identify duplicates
SELECT specs_hash, COUNT(*) as duplicate_count 
FROM hw_bom 
GROUP BY specs_hash 
HAVING COUNT(*) > 1;

-- Step 3: Merge duplicates (requires careful FK reference updates)
-- This would be handled by a migration script
```

#### Benefits of Hash-Based Approach

1. **Automatic Deduplication**: Same specs always get same ID
2. **Simplified Analytics**: No need for complex deduplication queries
3. **Storage Optimization**: Single record per unique configuration
4. **Consistent Reporting**: Same configurations properly grouped
5. **Fast Lookups**: Hash-based retrieval is very efficient

#### Alternative Approaches Considered

1. **Composite Natural Keys**: Use meaningful hardware/software identifiers
   - Pros: Human-readable, business meaningful
   - Cons: Complex key management, nullable components

2. **Content-Based UUIDs**: UUID v5 based on specs content
   - Pros: Still uses UUID format, deterministic
   - Cons: Less efficient than direct hash comparison

3. **Separate Lookup Tables**: Normalize individual components
   - Pros: True relational design, component reuse
   - Cons: Complex schema, loses JSON flexibility

## Performance Considerations

### Indexing Strategy

```sql
-- Primary performance indexes
CREATE INDEX idx_test_runs_created ON test_runs(created_at);
CREATE INDEX idx_test_runs_type ON test_runs(test_type_id);
CREATE INDEX idx_test_runs_env ON test_runs(environment_id);
CREATE INDEX idx_sw_kernel ON sw_bom(kernel_version);

-- JSON extraction indexes (MySQL 8.0+)
CREATE INDEX idx_hw_cpu_model ON hw_bom((JSON_UNQUOTE(JSON_EXTRACT(specs, '$.cpu.model'))));
CREATE INDEX idx_sw_os_name ON sw_bom((JSON_UNQUOTE(JSON_EXTRACT(specs, '$.os.name'))));
```

### Query Optimization

1. **Use Generated Columns**: Extract frequently queried JSON fields
2. **Partition Large Tables**: Consider partitioning results tables by date
3. **Materialized Views**: For complex aggregations used in dashboards
4. **Connection Pooling**: Implement proper connection management

## Data Validation

### JSON Schema Validation

Each BOM and environment includes JSON schema validation:

```sql
-- Ensure JSON validity
CHECK (JSON_VALID(specs))
CHECK (JSON_VALID(tools))
CHECK (JSON_VALID(env_metadata))
```

### Application-Level Validation

- JSON Schema validation against contracts
- Business rule validation for acceptance criteria
- Data consistency checks during import

## Security Considerations

1. **Connection Security**: Use SSL/TLS for database connections
2. **Access Control**: Implement role-based database access
3. **Audit Logging**: Track data modifications for compliance
4. **Data Encryption**: Consider encryption at rest for sensitive data

## Monitoring and Maintenance

### Database Health Monitoring

1. **Performance Metrics**: Query response times, connection pools
2. **Storage Monitoring**: Table sizes, index efficiency
3. **Query Analysis**: Slow query identification and optimization
4. **Backup Validation**: Regular backup testing and restoration

### Maintenance Tasks

1. **Statistics Updates**: Keep table statistics current for optimizer
2. **Index Maintenance**: Monitor and rebuild fragmented indexes
3. **Data Archival**: Archive old test results based on retention policy
4. **Schema Evolution**: Manage schema changes with proper migrations

## Future Enhancements

### Planned Extensions

1. **Additional Result Tables**: `results_io`, `results_network`, `results_security`
2. **Test Execution Tracking**: Real-time test status and progress
3. **Data Lake Integration**: Export to analytics platforms
4. **Advanced Analytics**: Machine learning on performance trends

### Scalability Considerations

1. **Read Replicas**: Separate analytics workload from operational queries
2. **Sharding Strategy**: Partition by test type or time period
3. **Caching Layer**: Redis for frequently accessed reference data
4. **Archive Strategy**: Move historical data to cheaper storage