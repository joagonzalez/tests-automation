"""Configuration module for benchmark analyzer."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv


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
    upload_dir: Path
    logs_dir: Path

    def __post_init__(self) -> None:
        """Ensure all paths are Path objects."""
        self.base_dir = Path(self.base_dir)
        self.contracts_dir = Path(self.contracts_dir)
        self.test_types_dir = Path(self.test_types_dir)
        self.environments_dir = Path(self.environments_dir)
        self.artifacts_dir = Path(self.artifacts_dir)
        self.temp_dir = Path(self.temp_dir)
        self.upload_dir = Path(self.upload_dir)
        self.logs_dir = Path(self.logs_dir)


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    enable_file_logging: bool = False


@dataclass
class SecurityConfig:
    """Security configuration."""

    secret_key: str = "your-very-secret-key-change-in-production"
    enable_auth: bool = False
    max_file_size: int = 104857600  # 100MB


class Config:
    """Main configuration class."""

    def __init__(self, env_file: Optional[str] = None) -> None:
        """Initialize configuration."""
        self._load_env_file(env_file)

        # Initialize sub-configurations
        self.database = self._init_database_config()
        self.api = self._init_api_config()
        self.paths = self._init_path_config()
        self.logging = self._init_logging_config()
        self.security = self._init_security_config()

        # Additional settings
        self.environment = self._get_environment()
        self.debug = self._get_debug_mode()

    def _load_env_file(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from .env file."""
        if env_file:
            # Load specific env file
            load_dotenv(env_file, override=True)
        else:
            # Try to find .env file in current directory or parent directories
            env_path = Path.cwd()
            while env_path != env_path.parent:
                env_file_path = env_path / ".env"
                if env_file_path.exists():
                    load_dotenv(env_file_path, override=True)
                    break
                env_path = env_path.parent
            else:
                # Try one more time in the script's directory
                script_dir = Path(__file__).parent
                env_file_path = script_dir / ".env"
                if env_file_path.exists():
                    load_dotenv(env_file_path, override=True)

    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def _get_env_int(self, key: str, default: int) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _get_env_list(self, key: str, default: list = None, separator: str = ",") -> list:
        """Get list environment variable."""
        if default is None:
            default = []
        value = os.getenv(key)
        if value:
            return [item.strip() for item in value.split(separator) if item.strip()]
        return default

    def _init_database_config(self) -> DatabaseConfig:
        """Initialize database configuration."""
        return DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=self._get_env_int('DB_PORT', 3306),
            username=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'perf_framework'),
            driver=os.getenv('DB_DRIVER', 'pymysql')
        )

    def _init_api_config(self) -> APIConfig:
        """Initialize API configuration."""
        return APIConfig(
            host=os.getenv('API_HOST', '0.0.0.0'),
            port=self._get_env_int('API_PORT', 8000),
            debug=self._get_env_bool('API_DEBUG', False),
            reload=self._get_env_bool('API_RELOAD', False),
            workers=self._get_env_int('API_WORKERS', 1),
            log_level=os.getenv('API_LOG_LEVEL', 'info'),
            cors_origins=self._get_env_list('CORS_ORIGINS', ['*'])
        )

    def _init_path_config(self) -> PathConfig:
        """Initialize path configuration."""
        # Base directory - use current working directory if not specified
        base_dir = Path(os.getenv('BASE_DIR', Path.cwd()))

        # If BASE_DIR is not set, use the package directory
        if os.getenv('BASE_DIR') is None:
            base_dir = Path(__file__).parent

        return PathConfig(
            base_dir=base_dir,
            contracts_dir=Path(os.getenv('CONTRACTS_DIR', base_dir / 'contracts')),
            test_types_dir=Path(os.getenv('TEST_TYPES_DIR', base_dir / 'contracts' / 'tests')),
            environments_dir=Path(os.getenv('ENVIRONMENTS_DIR', base_dir / 'contracts' / 'environments')),
            artifacts_dir=Path(os.getenv('ARTIFACTS_DIR', base_dir / 'artifacts')),
            temp_dir=Path(os.getenv('TEMP_DIR', base_dir / 'temp')),
            upload_dir=Path(os.getenv('UPLOAD_DIR', base_dir / 'uploads')),
            logs_dir=Path(os.getenv('LOGS_DIR', base_dir / 'logs'))
        )

    def _init_logging_config(self) -> LoggingConfig:
        """Initialize logging configuration."""
        file_path = os.getenv('LOG_FILE_PATH')
        if file_path:
            file_path = Path(file_path)

        return LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=file_path,
            max_bytes=self._get_env_int('LOG_MAX_BYTES', 10485760),
            backup_count=self._get_env_int('LOG_BACKUP_COUNT', 5),
            enable_file_logging=self._get_env_bool('ENABLE_FILE_LOGGING', False)
        )

    def _init_security_config(self) -> SecurityConfig:
        """Initialize security configuration."""
        return SecurityConfig(
            secret_key=os.getenv('SECRET_KEY', 'your-very-secret-key-change-in-production'),
            enable_auth=self._get_env_bool('ENABLE_AUTH', False),
            max_file_size=self._get_env_int('MAX_FILE_SIZE', 104857600)
        )

    def _get_environment(self) -> str:
        """Get current environment."""
        return os.getenv('ENVIRONMENT', 'development')

    def _get_debug_mode(self) -> bool:
        """Get debug mode."""
        return self._get_env_bool('DEBUG', False)

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directories = [
            self.paths.contracts_dir,
            self.paths.test_types_dir,
            self.paths.environments_dir,
            self.paths.artifacts_dir,
            self.paths.temp_dir,
            self.paths.upload_dir,
            self.paths.logs_dir
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
                'temp_dir': str(self.paths.temp_dir),
                'upload_dir': str(self.paths.upload_dir),
                'logs_dir': str(self.paths.logs_dir)
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_path': str(self.logging.file_path) if self.logging.file_path else None,
                'max_bytes': self.logging.max_bytes,
                'backup_count': self.logging.backup_count,
                'enable_file_logging': self.logging.enable_file_logging
            },
            'security': {
                'enable_auth': self.security.enable_auth,
                'max_file_size': self.security.max_file_size
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None) -> Config:
    """Reload configuration."""
    global _config
    _config = Config(env_file)
    return _config
