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
            "required": ["iops", "throughput"],
            "properties": {
                "iops": {
                    "type": "object",
                    "required": ["read", "write"],
                    "properties": {
                        "read": {"type": "number", "minimum": 0},
                        "write": {"type": "number", "minimum": 0}
                    }
                },
                "throughput": {
                    "type": "object",
                    "required": ["sequential_read", "sequential_write"],
                    "properties": {
                        "sequential_read": {"type": "number", "minimum": 0},
                        "sequential_write": {"type": "number", "minimum": 0}
                    }
                }
            }
        }
    }
}