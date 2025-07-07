"""Unit tests for configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

from benchmark_analyzer.config import (
    Config,
    DatabaseConfig,
    APIConfig,
    PathConfig,
    LoggingConfig,
    get_config,
    reload_config,
)


class TestDatabaseConfig:
    """Test DatabaseConfig class."""

    def test_default_values(self):
        """Test default database configuration values."""
        db_config = DatabaseConfig()

        assert db_config.host == "localhost"
        assert db_config.port == 3306
        assert db_config.username == "root"
        assert db_config.password == ""
        assert db_config.database == "perf_framework"
        assert db_config.driver == "pymysql"

    def test_custom_values(self):
        """Test custom database configuration values."""
        db_config = DatabaseConfig(
            host="remote-db",
            port=3307,
            username="testuser",
            password="testpass",
            database="testdb",
            driver="mysqldb"
        )

        assert db_config.host == "remote-db"
        assert db_config.port == 3307
        assert db_config.username == "testuser"
        assert db_config.password == "testpass"
        assert db_config.database == "testdb"
        assert db_config.driver == "mysqldb"

    def test_url_generation(self):
        """Test database URL generation."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            username="user",
            password="pass",
            database="testdb",
            driver="pymysql"
        )

        expected_url = "mysql+pymysql://user:pass@localhost:3306/testdb"
        assert db_config.url == expected_url

    def test_url_safe_generation(self):
        """Test safe database URL generation (masked password)."""
        db_config = DatabaseConfig(
            host="localhost",
            port=3306,
            username="user",
            password="secretpass",
            database="testdb"
        )

        expected_url = "mysql+pymysql://user:***@localhost:3306/testdb"
        assert db_config.url_safe == expected_url


class TestAPIConfig:
    """Test APIConfig class."""

    def test_default_values(self):
        """Test default API configuration values."""
        api_config = APIConfig()

        assert api_config.host == "0.0.0.0"
        assert api_config.port == 8000
        assert api_config.debug is False
        assert api_config.reload is False
        assert api_config.workers == 1
        assert api_config.log_level == "info"
        assert api_config.cors_origins == ["*"]

    def test_custom_values(self):
        """Test custom API configuration values."""
        cors_origins = ["http://localhost:3000", "https://example.com"]
        api_config = APIConfig(
            host="127.0.0.1",
            port=8080,
            debug=True,
            reload=True,
            workers=4,
            log_level="debug",
            cors_origins=cors_origins
        )

        assert api_config.host == "127.0.0.1"
        assert api_config.port == 8080
        assert api_config.debug is True
        assert api_config.reload is True
        assert api_config.workers == 4
        assert api_config.log_level == "debug"
        assert api_config.cors_origins == cors_origins

    def test_cors_origins_default(self):
        """Test CORS origins default behavior."""
        api_config = APIConfig(cors_origins=None)
        assert api_config.cors_origins == ["*"]


class TestPathConfig:
    """Test PathConfig class."""

    def test_path_conversion(self):
        """Test that paths are converted to Path objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path_config = PathConfig(
                base_dir=temp_dir,
                contracts_dir=f"{temp_dir}/contracts",
                test_types_dir=f"{temp_dir}/test_types",
                environments_dir=f"{temp_dir}/environments",
                artifacts_dir=f"{temp_dir}/artifacts",
                temp_dir=f"{temp_dir}/temp"
            )

            assert isinstance(path_config.base_dir, Path)
            assert isinstance(path_config.contracts_dir, Path)
            assert isinstance(path_config.test_types_dir, Path)
            assert isinstance(path_config.environments_dir, Path)
            assert isinstance(path_config.artifacts_dir, Path)
            assert isinstance(path_config.temp_dir, Path)


class TestLoggingConfig:
    """Test LoggingConfig class."""

    def test_default_values(self):
        """Test default logging configuration values."""
        log_config = LoggingConfig()

        assert log_config.level == "INFO"
        assert log_config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert log_config.file_path is None
        assert log_config.max_bytes == 10485760
        assert log_config.backup_count == 5

    def test_file_path_conversion(self):
        """Test file path conversion to Path object."""
        log_config = LoggingConfig(file_path="/tmp/test.log")
        assert isinstance(log_config.file_path, Path)
        assert str(log_config.file_path) == "/tmp/test.log"


class TestConfig:
    """Test main Config class."""

    def setup_method(self):
        """Set up test method."""
        # Clear any existing global config
        import benchmark_analyzer.config
        benchmark_analyzer.config._config = None

    def test_default_config(self):
        """Test default configuration without files or environment variables."""
        config = Config()

        # Test database defaults
        assert config.database.host == "localhost"
        assert config.database.port == 3306
        assert config.database.username == "root"
        assert config.database.database == "perf_framework"

        # Test API defaults
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 8000
        assert config.api.debug is False

        # Test environment detection
        assert config.environment in ["development", "production"]
        assert isinstance(config.debug, bool)

    @patch.dict(os.environ, {
        'DB_HOST': 'test-host',
        'DB_PORT': '3307',
        'DB_USER': 'test-user',
        'DB_PASSWORD': 'test-pass',
        'DB_NAME': 'test-db',
        'API_HOST': '127.0.0.1',
        'API_PORT': '8080',
        'API_DEBUG': 'true',
        'ENVIRONMENT': 'testing',
        'DEBUG': 'true'
    })
    def test_environment_variables(self):
        """Test configuration loading from environment variables."""
        config = Config()

        assert config.database.host == "test-host"
        assert config.database.port == 3307
        assert config.database.username == "test-user"
        assert config.database.password == "test-pass"
        assert config.database.database == "test-db"

        assert config.api.host == "127.0.0.1"
        assert config.api.port == 8080
        assert config.api.debug is True

        assert config.environment == "testing"
        assert config.debug is True

    def test_yaml_config_file(self):
        """Test configuration loading from YAML file."""
        config_data = {
            'database': {
                'host': 'yaml-host',
                'port': 3308,
                'username': 'yaml-user',
                'password': 'yaml-pass'
            },
            'api': {
                'host': '0.0.0.0',
                'port': 9000,
                'debug': True
            },
            'environment': 'production'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            config = Config(config_file)

            assert config.database.host == "yaml-host"
            assert config.database.port == 3308
            assert config.database.username == "yaml-user"
            assert config.database.password == "yaml-pass"

            assert config.api.host == "0.0.0.0"
            assert config.api.port == 9000
            assert config.api.debug is True

            assert config.environment == "production"
        finally:
            os.unlink(config_file)

    @patch.dict(os.environ, {'DB_HOST': 'env-host'})
    def test_environment_override_yaml(self):
        """Test that environment variables override YAML configuration."""
        config_data = {
            'database': {
                'host': 'yaml-host',
                'port': 3308
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            config = Config(config_file)

            # Environment variable should override YAML
            assert config.database.host == "env-host"
            # YAML value should be preserved for non-overridden values
            assert config.database.port == 3308
        finally:
            os.unlink(config_file)

    def test_db_url_property(self):
        """Test database URL property."""
        config = Config()
        expected_url = config.database.url
        assert config.db_url == expected_url

    def test_is_development(self):
        """Test development environment detection."""
        config = Config()
        config.environment = "development"
        assert config.is_development is True

        config.environment = "dev"
        assert config.is_development is True

        config.environment = "production"
        assert config.is_development is False

    def test_is_production(self):
        """Test production environment detection."""
        config = Config()
        config.environment = "production"
        assert config.is_production is True

        config.environment = "prod"
        assert config.is_production is True

        config.environment = "development"
        assert config.is_production is False

    def test_to_dict(self):
        """Test configuration conversion to dictionary."""
        config = Config()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'environment' in config_dict
        assert 'debug' in config_dict
        assert 'database' in config_dict
        assert 'api' in config_dict
        assert 'paths' in config_dict
        assert 'logging' in config_dict

        # Check nested structure
        assert 'host' in config_dict['database']
        assert 'port' in config_dict['database']
        assert 'url' in config_dict['database']

        # Check that password is masked in URL
        assert '***' in config_dict['database']['url']

    def test_get_method(self):
        """Test get method for retrieving configuration values."""
        config = Config()

        # Test existing key
        environment = config.get('environment')
        assert environment is not None

        # Test non-existing key with default
        value = config.get('non_existing_key', 'default_value')
        assert value == 'default_value'

        # Test non-existing key without default
        value = config.get('non_existing_key')
        assert value is None

    @patch('benchmark_analyzer.config.Path.mkdir')
    def test_ensure_directories(self, mock_mkdir):
        """Test ensure directories functionality."""
        config = Config()
        config.ensure_directories()

        # Check that mkdir was called for each directory
        assert mock_mkdir.call_count >= 5  # At least 5 directories should be created

    def test_convert_env_value(self):
        """Test environment value conversion."""
        config = Config()

        # Test boolean conversion
        assert config._convert_env_value('true') is True
        assert config._convert_env_value('false') is False
        assert config._convert_env_value('True') is True
        assert config._convert_env_value('False') is False

        # Test integer conversion
        assert config._convert_env_value('123') == 123
        assert config._convert_env_value('-456') == -456

        # Test float conversion
        assert config._convert_env_value('123.45') == 123.45
        assert config._convert_env_value('-67.89') == -67.89

        # Test string (no conversion)
        assert config._convert_env_value('some_string') == 'some_string'

    def test_invalid_config_file(self):
        """Test handling of invalid configuration file."""
        with pytest.raises(ValueError, match="Unsupported config file format"):
            Config("invalid_file.txt")

    def test_nonexistent_config_file(self):
        """Test handling of non-existent configuration file."""
        # Should not raise an error, should use defaults
        config = Config("non_existent_file.yaml")
        assert config.database.host == "localhost"  # Should use default


class TestGlobalConfigFunctions:
    """Test global configuration functions."""

    def setup_method(self):
        """Set up test method."""
        # Clear any existing global config
        import benchmark_analyzer.config
        benchmark_analyzer.config._config = None

    def test_get_config(self):
        """Test get_config function."""
        config1 = get_config()
        config2 = get_config()

        # Should return the same instance (singleton pattern)
        assert config1 is config2

    def test_reload_config(self):
        """Test reload_config function."""
        config1 = get_config()
        config2 = reload_config()

        # Should return a new instance
        assert config1 is not config2

    @patch.dict(os.environ, {'DB_HOST': 'test-reload'})
    def test_reload_config_with_env_change(self):
        """Test reload_config with environment variable changes."""
        # Get initial config
        config1 = get_config()
        initial_host = config1.database.host

        # Reload config should pick up the new environment variable
        config2 = reload_config()
        assert config2.database.host == 'test-reload'
        assert config2.database.host != initial_host
