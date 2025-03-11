Usage examples:

```bash
# Import results
python -m src.main import-results artifacts/test_results.yaml --environment artifacts/environment.yaml

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

# Run with default settings
python -m src.main dashboard

# Run on a specific port
python -m src.main dashboard --port 8502

# Run with a specific database
python -m src.main dashboard --db-path artifacts/benchmark_results.db
```

