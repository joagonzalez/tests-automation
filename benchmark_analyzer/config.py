# config.py
from pathlib import Path
from typing import Dict, Any
import yaml
import os

class Config:
    """Application configuration manager."""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from YAML file and environment variables."""
        config_path = Path("config.yaml")

        # Load from file if exists
        if config_path.exists():
            with open(config_path) as f:
                self._config = yaml.safe_load(f)

        # Override with environment variables
        self._config["database"] = {
            "url": os.getenv("BENCHMARK_DB_URL", "sqlite:///benchmark_results.db")
        }

        self._config["contracts_path"] = os.getenv(
            "BENCHMARK_CONTRACTS_PATH",
            "benchmark_analyzer/contracts"
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    @property
    def db_url(self) -> str:
        """Get database URL."""
        return self._config["database"]["url"]

    @property
    def contracts_path(self) -> Path:
        """Get contracts directory path."""
        return Path(self._config["contracts_path"])
