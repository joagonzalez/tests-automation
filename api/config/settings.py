"""API configuration settings."""

import os
from typing import Dict, Any, List

# Main configuration dictionary
config: Dict[str, Any] = {
    # Server configuration
    "server": {
        "host": os.getenv("API_HOST", "0.0.0.0"),
        "port": int(os.getenv("API_PORT", "8000")),
        "reload": os.getenv("API_RELOAD", "false").lower() == "true",
        "workers": int(os.getenv("API_WORKERS", "1")),
        "log_level": os.getenv("API_LOG_LEVEL", "info"),
    },

    # Application configuration
    "app": {
        "title": "Benchmark Analyzer API",
        "description": "API for managing benchmark test results and analysis",
        "version": "0.1.0",
        "debug": os.getenv("API_DEBUG", "false").lower() == "true",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    },

    # Database configuration
    "database": {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "username": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "perf_framework"),
        "driver": os.getenv("DB_DRIVER", "pymysql"),
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        "echo": os.getenv("DB_ECHO", "false").lower() == "true",
    },

    # CORS configuration
    "cors": {
        "allow_origins": [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        ],
        "allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        "allow_methods": [
            method.strip()
            for method in os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
        ],
        "allow_headers": [
            header.strip()
            for header in os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
        ],
    },

    # Security configuration
    "security": {
        "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
        "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
        "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        "api_key_header": os.getenv("API_KEY_HEADER", "X-API-Key"),
        "api_key": os.getenv("API_KEY", ""),
        "enable_auth": os.getenv("ENABLE_AUTH", "false").lower() == "true",
    },

    # File upload configuration
    "upload": {
        "max_file_size": int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024,  # 100MB default
        "allowed_extensions": [
            ext.strip()
            for ext in os.getenv("ALLOWED_EXTENSIONS", ".zip,.json,.csv,.yaml,.yml").split(",")
        ],
        "upload_dir": os.getenv("UPLOAD_DIR", "uploads"),
        "temp_dir": os.getenv("TEMP_DIR", "temp"),
    },

    # Logging configuration
    "logging": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        "file_path": os.getenv("LOG_FILE_PATH", ""),
        "max_bytes": int(os.getenv("LOG_MAX_BYTES", "10485760")),  # 10MB
        "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
        "enable_file_logging": os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true",
    },

    # Rate limiting configuration
    "rate_limit": {
        "enabled": os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true",
        "requests_per_minute": int(os.getenv("RATE_LIMIT_RPM", "60")),
        "requests_per_hour": int(os.getenv("RATE_LIMIT_RPH", "1000")),
        "requests_per_day": int(os.getenv("RATE_LIMIT_RPD", "10000")),
    },

    # Cache configuration
    "cache": {
        "enabled": os.getenv("CACHE_ENABLED", "false").lower() == "true",
        "backend": os.getenv("CACHE_BACKEND", "memory"),  # memory, redis
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "default_ttl": int(os.getenv("CACHE_DEFAULT_TTL", "300")),  # 5 minutes
        "max_size": int(os.getenv("CACHE_MAX_SIZE", "1000")),
    },

    # Monitoring configuration
    "monitoring": {
        "enable_metrics": os.getenv("ENABLE_METRICS", "false").lower() == "true",
        "metrics_endpoint": os.getenv("METRICS_ENDPOINT", "/metrics"),
        "health_endpoint": os.getenv("HEALTH_ENDPOINT", "/health"),
        "enable_tracing": os.getenv("ENABLE_TRACING", "false").lower() == "true",
    },

    # Pagination configuration
    "pagination": {
        "default_page_size": int(os.getenv("DEFAULT_PAGE_SIZE", "50")),
        "max_page_size": int(os.getenv("MAX_PAGE_SIZE", "1000")),
    },

    # Background tasks configuration
    "background_tasks": {
        "enabled": os.getenv("BACKGROUND_TASKS_ENABLED", "false").lower() == "true",
        "worker_count": int(os.getenv("BACKGROUND_WORKER_COUNT", "2")),
        "queue_size": int(os.getenv("BACKGROUND_QUEUE_SIZE", "100")),
    },

    # External services configuration
    "external_services": {
        "grafana": {
            "base_url": os.getenv("GRAFANA_BASE_URL", "http://localhost:3000"),
            "api_key": os.getenv("GRAFANA_API_KEY", ""),
            "timeout": int(os.getenv("GRAFANA_TIMEOUT", "30")),
        },
        "notification": {
            "webhook_url": os.getenv("NOTIFICATION_WEBHOOK_URL", ""),
            "email_smtp_server": os.getenv("EMAIL_SMTP_SERVER", ""),
            "email_smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
            "email_username": os.getenv("EMAIL_USERNAME", ""),
            "email_password": os.getenv("EMAIL_PASSWORD", ""),
        },
    },

    # Environment configuration
    "environment": {
        "name": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "testing": os.getenv("TESTING", "false").lower() == "true",
    },
}


def get_database_url() -> str:
    """Get database URL from configuration."""
    db_config = config["database"]
    return (
        f"mysql+{db_config['driver']}://"
        f"{db_config['username']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/"
        f"{db_config['database']}"
    )


def get_database_url_safe() -> str:
    """Get database URL with masked password for logging."""
    db_config = config["database"]
    return (
        f"mysql+{db_config['driver']}://"
        f"{db_config['username']}:***@"
        f"{db_config['host']}:{db_config['port']}/"
        f"{db_config['database']}"
    )


def is_development() -> bool:
    """Check if running in development environment."""
    return config["environment"]["name"].lower() in ("development", "dev")


def is_production() -> bool:
    """Check if running in production environment."""
    return config["environment"]["name"].lower() in ("production", "prod")


def is_testing() -> bool:
    """Check if running in testing environment."""
    return config["environment"]["testing"]


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation.

    Args:
        key_path: Dot-separated path to the configuration key
        default: Default value if key is not found

    Returns:
        Configuration value or default

    Example:
        get_config_value("server.port", 8000)
    """
    keys = key_path.split(".")
    value = config

    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def update_config(key_path: str, value: Any) -> None:
    """
    Update configuration value using dot notation.

    Args:
        key_path: Dot-separated path to the configuration key
        value: New value to set

    Example:
        update_config("server.port", 8080)
    """
    keys = key_path.split(".")
    current = config

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value


def validate_config() -> List[str]:
    """
    Validate configuration and return list of errors.

    Returns:
        List of validation errors
    """
    errors = []

    # Check required database configuration
    if not config["database"]["host"]:
        errors.append("Database host is required")

    if not config["database"]["username"]:
        errors.append("Database username is required")

    if not config["database"]["database"]:
        errors.append("Database name is required")

    # Check server configuration
    if config["server"]["port"] <= 0 or config["server"]["port"] > 65535:
        errors.append("Server port must be between 1 and 65535")

    # Check security configuration
    if config["security"]["enable_auth"] and not config["security"]["secret_key"]:
        errors.append("Secret key is required when authentication is enabled")

    if config["security"]["enable_auth"] and config["security"]["secret_key"] == "your-secret-key-here":
        errors.append("Default secret key must be changed in production")

    # Check file upload configuration
    if config["upload"]["max_file_size"] <= 0:
        errors.append("Maximum file size must be greater than 0")

    return errors


# Validate configuration on import
_validation_errors = validate_config()
if _validation_errors and not is_testing():
    import warnings
    for error in _validation_errors:
        warnings.warn(f"Configuration error: {error}")
