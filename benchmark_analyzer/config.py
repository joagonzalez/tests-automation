"""Configuration module for benchmark analyzer."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse

import yaml


@dataclass
class DatabaseConfig:
    """Database configuration."""

    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "perf_framework"
    driver: str = "pymysql"

    @property
    def url(self) -> str:
        """Get database URL."""
        return f"mysql+{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def url_safe(self) -> str:
        """Get database URL with masked password for logging."""
        return f"mysql+{self.driver}://{self.username}:***@{self.host}:{self.port}/{self.database}"


@dataclass
class APIConfig:
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    cors_origins: list = None

    def __post_init__(self) -> None:
        """Post-init processing."""
        if self.cors_origins is None:
            self.cors_origins = ["*"]


@dataclass
class PathConfig:
    """Path configuration."""

    base_dir: Path
    contracts_dir: Path
    test_types_dir: Path
    environments_dir: Path
    artifacts_dir: Path
    temp_dir: Path

    def __post_init__(self) -> None:
        """Ensure all paths are Path objects."""
        self.base_dir = Path(self.base_dir)
        self.contracts_dir = Path(self.contracts_dir)
        self.test_types_dir = Path(self.test_types_dir)
        self.environments_dir = Path(self.environments_dir)
        self.artifacts_dir = Path(self.artifacts_dir)
        self.temp_dir = Path(self.temp_dir)


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5


class Config:
    """Main configuration class."""

    def __init__(self, config_file: Optional[str] = None) -> None:
        """Initialize configuration."""
        self._config_data: Dict[str, Any] = {}
        self._load_config(config_file)

        # Initialize sub-configurations
        self.database = self._init_database_config()
        self.api = self._init_api_config()
        self.paths = self._init_path_config()
        self.logging = self._init_logging_config()

        # Additional settings
        self.environment = self._get_environment()
        self.debug = self._get_debug_mode()

    def _load_config(self, config_file: Optional[str] = None) -> None:
        """Load configuration from file or environment."""
        # Load from file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    self._config_data = yaml.safe_load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_file}")

        # Override with environment variables
        self._load_env_variables()

    def _load_env_variables(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            'DB_HOST': ['database', 'host'],
            'DB_PORT': ['database', 'port'],
            'DB_USER': ['database', 'username'],
            'DB_PASSWORD': ['database', 'password'],
            'DB_NAME': ['database', 'database'],
            'API_HOST': ['api', 'host'],
            'API_PORT': ['api', 'port'],
            'API_DEBUG': ['api', 'debug'],
            'LOG_LEVEL': ['logging', 'level'],
            'ENVIRONMENT': ['environment'],
            'DEBUG': ['debug'],
        }

        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_config(config_path, self._convert_env_value(value))

    def _set_nested_config(self, path: list, value: Any) -> None:
        """Set nested configuration value."""
        current = self._config_data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _init_database_config(self) -> DatabaseConfig:
        """Initialize database configuration."""
        db_config = self._config_data.get('database', {})
        return DatabaseConfig(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 3306),
            username=db_config.get('username', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'perf_framework'),
            driver=db_config.get('driver', 'pymysql')
        )

    def _init_api_config(self) -> APIConfig:
        """Initialize API configuration."""
        api_config = self._config_data.get('api', {})
        return APIConfig(
            host=api_config.get('host', '0.0.0.0'),
            port=api_config.get('port', 8000),
            debug=api_config.get('debug', False),
            reload=api_config.get('reload', False),
            workers=api_config.get('workers', 1),
            log_level=api_config.get('log_level', 'info'),
            cors_origins=api_config.get('cors_origins', ['*'])
        )

    def _init_path_config(self) -> PathConfig:
        """Initialize path configuration."""
        base_dir = Path(__file__).parent
        paths_config = self._config_data.get('paths', {})

        return PathConfig(
            base_dir=Path(paths_config.get('base_dir', base_dir)),
            contracts_dir=Path(paths_config.get('contracts_dir', base_dir / 'contracts')),
            test_types_dir=Path(paths_config.get('test_types_dir', base_dir / 'contracts' / 'tests')),
            environments_dir=Path(paths_config.get('environments_dir', base_dir / 'contracts' / 'environments')),
            artifacts_dir=Path(paths_config.get('artifacts_dir', base_dir / 'artifacts')),
            temp_dir=Path(paths_config.get('temp_dir', base_dir / 'temp'))
        )

    def _init_logging_config(self) -> LoggingConfig:
        """Initialize logging configuration."""
        logging_config = self._config_data.get('logging', {})

        file_path = logging_config.get('file_path')
        if file_path:
            file_path = Path(file_path)

        return LoggingConfig(
            level=logging_config.get('level', 'INFO'),
            format=logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=file_path,
            max_bytes=logging_config.get('max_bytes', 10485760),
            backup_count=logging_config.get('backup_count', 5)
        )

    def _get_environment(self) -> str:
        """Get current environment."""
        return self._config_data.get('environment', os.getenv('ENVIRONMENT', 'development'))

    def _get_debug_mode(self) -> bool:
        """Get debug mode."""
        return self._config_data.get('debug', os.getenv('DEBUG', 'false').lower() == 'true')

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        return self._config_data.get(key, default)

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directories = [
            self.paths.contracts_dir,
            self.paths.test_types_dir,
            self.paths.environments_dir,
            self.paths.artifacts_dir,
            self.paths.temp_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def db_url(self) -> str:
        """Get database URL."""
        return self.database.url

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ('development', 'dev')

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ('production', 'prod')

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'username': self.database.username,
                'database': self.database.database,
                'driver': self.database.driver,
                'url': self.database.url_safe
            },
            'api': {
                'host': self.api.host,
                'port': self.api.port,
                'debug': self.api.debug,
                'reload': self.api.reload,
                'workers': self.api.workers,
                'log_level': self.api.log_level,
                'cors_origins': self.api.cors_origins
            },
            'paths': {
                'base_dir': str(self.paths.base_dir),
                'contracts_dir': str(self.paths.contracts_dir),
                'test_types_dir': str(self.paths.test_types_dir),
                'environments_dir': str(self.paths.environments_dir),
                'artifacts_dir': str(self.paths.artifacts_dir),
                'temp_dir': str(self.paths.temp_dir)
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_path': str(self.logging.file_path) if self.logging.file_path else None,
                'max_bytes': self.logging.max_bytes,
                'backup_count': self.logging.backup_count
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_file)
    return _config


def reload_config(config_file: Optional[str] = None) -> Config:
    """Reload configuration."""
    global _config
    _config = Config(config_file)
    return _config
