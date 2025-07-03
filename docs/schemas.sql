
-- ===============================================================
--  Benchmark & Acceptance Framework
--  MySQL 8.4.3 – Option A (UUID CHAR(36) generated in app layer)
--  Author: Joaquin Gonzalez · Generated: 2025-07-03 15:01:17
-- ===============================================================

-- Make sure the DB exists (adjust name as needed)
CREATE DATABASE IF NOT EXISTS perf_framework
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE perf_framework;

-- ---------------------------------------------------------------
-- 1. Lookup tables
-- ---------------------------------------------------------------

CREATE TABLE operators (
    op_id       TINYINT      PRIMARY KEY,  -- 1=lt,2=lte,3=eq,4=neq,5=gt,6=gte,7=btw
    code        VARCHAR(8)   UNIQUE NOT NULL,
    description VARCHAR(64)
) ENGINE=InnoDB;

INSERT INTO operators (op_id, code, description) VALUES
 (1,'lt',  '<'),
 (2,'lte', '<='),
 (3,'eq',  '='),
 (4,'neq', '!='),
 (5,'gt',  '>'),
 (6,'gte', '>='),
 (7,'btw', 'between');

CREATE TABLE test_types (
    test_type_id  CHAR(36) PRIMARY KEY,
    name          VARCHAR(64) UNIQUE NOT NULL,
    description   TEXT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- 2. Dimension tables
-- ---------------------------------------------------------------

CREATE TABLE environments (
    id          CHAR(36) PRIMARY KEY,
    name        VARCHAR(128),
    type        VARCHAR(32),       -- cloud, bare-metal, vm, etc.
    comments    TEXT,
    tools       JSON,              -- toolchain versions
    metadata    JSON,              -- arbitrary extra info
    CHECK (JSON_VALID(tools)),
    CHECK (JSON_VALID(metadata))
) ENGINE=InnoDB;

CREATE TABLE hw_bom (
    bom_id      CHAR(36) PRIMARY KEY,
    specs       JSON NOT NULL,
    CHECK (JSON_VALID(specs))
) ENGINE=InnoDB;

CREATE TABLE sw_bom (
    bom_id      CHAR(36) PRIMARY KEY,
    specs       JSON NOT NULL,
    CHECK (JSON_VALID(specs)),

    -- Example generated column for quick filtering/indexing
    kernel_version VARCHAR(50) GENERATED ALWAYS AS
        (JSON_UNQUOTE(JSON_EXTRACT(specs, '$.kernel_version'))) STORED,
    INDEX idx_sw_kernel (kernel_version)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- 3. Fact table
-- ---------------------------------------------------------------

CREATE TABLE test_runs (
    test_run_id     CHAR(36) PRIMARY KEY,
    test_type_id    CHAR(36) NOT NULL,
    environment_id  CHAR(36),
    hw_bom_id       CHAR(36),
    sw_bom_id       CHAR(36),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    engineer        VARCHAR(64),
    comments        TEXT,
    configuration   JSON,

    CHECK (JSON_VALID(configuration)),

    FOREIGN KEY (test_type_id)   REFERENCES test_types(test_type_id),
    FOREIGN KEY (environment_id) REFERENCES environments(id),
    FOREIGN KEY (hw_bom_id)      REFERENCES hw_bom(bom_id),
    FOREIGN KEY (sw_bom_id)      REFERENCES sw_bom(bom_id),

    INDEX idx_test_runs_created (created_at)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- 4. Results tables (one per family)
--    Example: CPU + Memory micro‑benchmarks
-- ---------------------------------------------------------------

CREATE TABLE results_cpu_mem (
    test_run_id  CHAR(36) PRIMARY KEY,

    memory_idle_latency_ns              DOUBLE,
    memory_peak_injection_bandwidth_mbs DOUBLE,
    ramspeed_smp_bandwidth_mbs_add      DOUBLE,
    ramspeed_smp_bandwidth_mbs_copy     DOUBLE,
    sysbench_ram_memory_bandwidth_mibs  INT,
    sysbench_ram_memory_test_duration_sec INT,
    sysbench_ram_memory_test_mode       VARCHAR(8),
    sysbench_cpu_events_per_second      INT,
    sysbench_cpu_duration_sec           INT,
    sysbench_cpu_test_mode              VARCHAR(16),

    FOREIGN KEY (test_run_id)
        REFERENCES test_runs(test_run_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- (🛈)  Add additional `results_xyz` tables for fio, iperf, pgbench, etc.,
--      each with its own metric columns but the same PK = test_run_id.

-- ---------------------------------------------------------------
-- 5. Acceptance criteria
-- ---------------------------------------------------------------

CREATE TABLE acceptance_criteria (
    id               CHAR(36) PRIMARY KEY,
    test_type_id     CHAR(36) NOT NULL,
    metric           VARCHAR(64) NOT NULL,
    op_id            TINYINT    NOT NULL,
    threshold_min    DOUBLE,
    threshold_max    DOUBLE,
    target_component VARCHAR(32),      -- cpu, memory, disk, network...

    FOREIGN KEY (test_type_id) REFERENCES test_types(test_type_id),
    FOREIGN KEY (op_id)        REFERENCES operators(op_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------
-- 6. Sample query helper view (optional)
-- ---------------------------------------------------------------

CREATE OR REPLACE VIEW v_test_runs_summary AS
SELECT
    tr.*,
    JSON_UNQUOTE(JSON_EXTRACT(sw.specs,'$.kernel_version')) AS kernel_version,
    tt.name AS test_name
FROM test_runs tr
LEFT JOIN sw_bom     sw ON sw.bom_id = tr.sw_bom_id
LEFT JOIN test_types tt ON tt.test_type_id = tr.test_type_id;

-- ---------------------------------------------------------------
-- Done.
-- ===============================================================
