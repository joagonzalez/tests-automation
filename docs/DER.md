# Benchmark & Acceptance Framework – Logical Schema

---

## 1. `environments`
| Column | Type | Notes |
| ------ | ---- | ----- |
| `id` (PK) | `TEXT` | Unique identifier (e.g., `lab-1`, `aws-c5n`, …) |
| `name` | `TEXT` | Friendly label (`“K8s Cluster A – Staging”`) |
| `type` | `TEXT` | Cloud, on‑prem, bare‑metal, VM, etc. |
| `comments` | `TEXT` | Free‑form notes |
| `tools` | `JSON` | Toolchain versions deployed in that env (Terraform, Helm, …) |
| `metadata` | `JSON` | Anything else (AZs, tags, region, …) |

*Relationship*: One **environment** ⟶ many **`test_runs`** (`environment_id`).

---

## 2. Bills‑of‑Material

### `hw_bom`
| Column | Type | Notes |
| ------ | ---- | ----- |
| `bom_id` (PK) | `TEXT` |
| `specs` | `JSON` | CPU model, cores, RAM, NICs, storage layout, BIOS tweaks… |

### `sw_bom`
| Column | Type | Notes |
| ------ | ---- | ----- |
| `bom_id` (PK) | `TEXT` |
| `specs` | `JSON` | Kernel, container runtime, driver versions, OS tuning… |

*Relationships*
* One *hardware* BoM ➡️ many **`test_runs`** (`hw_bom_id`).
* One *software* BoM ➡️ many **`test_runs`** (`sw_bom_id`).

---

## 3. `test_runs`
| Column | Type | Notes |
| ------ | ---- | ----- |
| `test_run_id` (PK) | `TEXT` |
| `test_type_id` (FK) | `TEXT` | Points to the matching _results_ table – see §4 |
| `environment_id` (FK) | `TEXT` |
| `hw_bom_id` (FK) | `TEXT` |
| `sw_bom_id` (FK) | `TEXT` |
| `created_at` | `DATETIME` |
| `engineer` | `TEXT` |
| `comments` | `TEXT` |
| `configuration` | `JSON` | Command‑line flags, pod spec, stress‑ng args, … |

Think of this as the **header row** for every benchmark execution.

---

## 4. Results per test type
Instead of one monster table, each benchmark family gets its **own, narrow results table**:

### `results_type_1`  *(example: “memory+CPU micro-bench”)*
| Column | Type | Sample metric |
| ------ | ---- | ------------- |
| `type_id` (PK) | `TEXT` | Same value referenced by `test_runs.test_type_id` |
| `test_type` | `TEXT` | e.g. `stress_ng` |
| `memory_idle_latency_ns` | `FLOAT` | |
| `memory_peak_injection_bandwidth_mbs` | `FLOAT` | |
| `ramspeed_smp_bandwidth_mbs_add` | `FLOAT` | |
| `ramspeed_smp_bandwidth_mbs_copy` | `FLOAT` | |
| `sysbench_ram_memory_bandwidth_mibs` | `INTEGER` | |
| `sysbench_ram_memory_test_duration_sec` | `INTEGER` | |
| `sysbench_ram_memory_test_mode` | `TEXT` | `seq` / `rnd`, … |
| `sysbench_cpu_events_per_second` | `INTEGER` | |
| `sysbench_cpu_duration_sec` | `INTEGER` | |
| `sysbench_cpu_test_mode` | `TEXT` | `threads=1` / `threads=16`, … |

*Add additional `results_type_n` tables for fio, iperf, pgbench, … – each with its own metric columns.*

*Relationship*: One row in a results table ↔︎ one row in **`test_runs`** (1‑to‑1 by `test_type_id`).

---

## 5. `acceptance_criteria`
| Column | Type | Notes |
| ------ | ---- | ----- |
| `id` (PK) | `TEXT` |
| `test_type_id` (FK) | `TEXT` | Which benchmark the rule applies to |
| `metric` | `TEXT` | Column name in the corresponding results table |
| `threshold` | `FLOAT / JSON` | Scalar, range, or complex structure |
| `operator` | `TEXT` | `>`, `<`, `>=`, `between`, … |
| `target_component` | `TEXT` | CPU, Memory, Disk, Network… |

Used to declare *“this run is valid only if latency < 5 µs”*-style gates.

---

## 6. Typical Queries

```sql
-- Join run metadata with its metrics
SELECT *
FROM   test_runs      AS t
JOIN   results_type_1 AS r ON t.test_type_id = r.type_id
WHERE  t.created_at >= NOW() - INTERVAL '7 days';
```

```sql
-- Filter runs by a value buried in the software BoM JSON
SELECT t.*
FROM   test_runs t
JOIN   sw_bom    b ON t.sw_bom_id = b.bom_id
WHERE  json_extract_path_text(b.specs,'nsx_t','version') = '4.0.1';
```

```sql
-- Validate a metric against its acceptance threshold
SELECT *
FROM   results_type_1 r
JOIN   acceptance_criteria a
       ON a.metric = 'sysbench_cpu_duration_sec'
WHERE  r.sysbench_cpu_duration_sec > CAST(a.threshold AS INTEGER)
  AND  a.operator = '>';
```

---

## 7. How the pieces fit

```text
environments   hw_bom   sw_bom
      \           |        /
       +-----------+-------+
                   |
               test_runs
                   |
          +--------+-------+
          |                |
 results_type_1  results_type_2 …   ← one table per test family
                   |
            acceptance_criteria
```

* Every **test run** binds an **environment** plus **H/W & S/W BoMs** to a concrete benchmark execution.
* Metrics live in a dedicated **results table** to keep schema evolution painless.
* **Acceptance rules** decouple pass/fail logic from the raw data.

---

**Forward‑looking thought:** Because IDs are all `TEXT`, migrating to UUIDs or ULIDs for global uniqueness later is just an `ALTER TABLE` away.
