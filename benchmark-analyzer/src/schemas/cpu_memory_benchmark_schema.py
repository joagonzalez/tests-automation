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
            "required": ["memory_latency", "ramspeed_smp", "sysbench"],
            "properties": {
                "memory_latency": {
                    "type": "object",
                    "required": ["idle_latency_ns", "peak_injection_bandwidth_mbs"],
                    "properties": {
                        "idle_latency_ns": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Memory latency in nanoseconds"
                        },
                        "peak_injection_bandwidth_mbs": {
                            "type": "number",
                            "minimum": 0,
                            "description": "Memory bandwidth in MB/s"
                        }
                    }
                },
                "ramspeed_smp": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "benchmark", "bandwidth_mbs"],
                        "properties": {
                            "type": {"type": "string"},
                            "benchmark": {"type": "string"},
                            "bandwidth_mbs": {
                                "type": "number",
                                "minimum": 0
                            }
                        }
                    }
                },
                "sysbench": {
                    "type": "object",
                    "required": ["ram_memory", "cpu"],
                    "properties": {
                        "ram_memory": {
                            "type": "object",
                            "required": ["bandwidth_mibs", "test_duration_sec"],
                            "properties": {
                                "bandwidth_mibs": {
                                    "type": "number",
                                    "minimum": 0
                                },
                                "test_duration_sec": {
                                    "type": "integer",
                                    "minimum": 1
                                },
                                "test_mode": {"type": "string"}
                            }
                        },
                        "cpu": {
                            "type": "object",
                            "required": ["events_per_sec", "test_duration_sec"],
                            "properties": {
                                "events_per_sec": {
                                    "type": "number",
                                    "minimum": 0
                                },
                                "test_duration_sec": {
                                    "type": "integer",
                                    "minimum": 1
                                },
                                "test_mode": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
}