"""Database connection manager for benchmark analyzer."""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any, Type

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base, MODEL_REGISTRY, Operator
from ..config import Config, get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize database manager."""
        self.config = config or get_config()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initialize database engine."""
        try:
            # Create engine with connection pooling
            self._engine = create_engine(
                self.config.database.url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=self.config.debug,
            )

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=True,
            )

            logger.info(f"Database engine initialized: {self.config.database.url_safe}")

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise

    @property
    def engine(self) -> Engine:
        """Get database engine."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with context manager."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def initialize_tables(self) -> None:
        """Initialize database tables."""
        try:
            # Create all tables
            Base.metadata.create_all(self.engine)

            # Initialize lookup data
            self._initialize_lookup_data()

            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
            raise

    def _initialize_lookup_data(self) -> None:
        """Initialize lookup table data."""
        try:
            with self.get_session() as session:
                # Check if operators table is empty
                operator_count = session.query(Operator).count()

                if operator_count == 0:
                    # Insert default operators
                    operators = [
                        Operator(op_id=1, code="lt", description="<"),
                        Operator(op_id=2, code="lte", description="<="),
                        Operator(op_id=3, code="eq", description="="),
                        Operator(op_id=4, code="neq", description="!="),
                        Operator(op_id=5, code="gt", description=">"),
                        Operator(op_id=6, code="gte", description=">="),
                        Operator(op_id=7, code="btw", description="between"),
                    ]

                    for operator in operators:
                        session.add(operator)

                    session.commit()
                    logger.info("Initialized operator lookup data")
                else:
                    logger.info("Operator lookup data already exists")

        except Exception as e:
            logger.error(f"Failed to initialize lookup data: {e}")
            raise

    def drop_all_tables(self) -> None:
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def clean_database(self) -> None:
        """Clean all data from database tables."""
        try:
            with self.get_session() as session:
                # Get all table names in reverse order to handle foreign keys
                tables = reversed(Base.metadata.sorted_tables)

                for table in tables:
                    session.execute(text(f"DELETE FROM {table.name}"))

                session.commit()

                # Re-initialize lookup data
                self._initialize_lookup_data()

                logger.info("Database cleaned successfully")
        except Exception as e:
            logger.error(f"Failed to clean database: {e}")
            raise

    def get_table_names(self) -> List[str]:
        """Get list of all table names."""
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            raise

    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a specific table."""
        try:
            with self.get_session() as session:
                result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.error(f"Failed to get row count for table {table_name}: {e}")
            raise

    def get_database_status(self) -> Dict[str, Any]:
        """Get comprehensive database status."""
        try:
            status = {
                "connection": self.test_connection(),
                "tables": {},
                "total_rows": 0,
            }

            table_names = self.get_table_names()

            for table_name in table_names:
                try:
                    row_count = self.get_table_row_count(table_name)
                    status["tables"][table_name] = row_count
                    status["total_rows"] += row_count
                except Exception as e:
                    status["tables"][table_name] = f"Error: {e}"

            return status
        except Exception as e:
            logger.error(f"Failed to get database status: {e}")
            return {"connection": False, "error": str(e)}

    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query and return results."""
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})

                # Handle different result types
                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return [{"affected_rows": result.rowcount}]

        except Exception as e:
            logger.error(f"Failed to execute raw query: {e}")
            raise

    def get_model_class(self, table_name: str) -> Optional[Type]:
        """Get SQLAlchemy model class for table name."""
        return MODEL_REGISTRY.get(table_name)

    def create_backup(self, backup_path: str) -> None:
        """Create database backup (MySQL dump)."""
        try:
            import subprocess

            # Build mysqldump command
            cmd = [
                "mysqldump",
                "-h", self.config.database.host,
                "-P", str(self.config.database.port),
                "-u", self.config.database.username,
                f"-p{self.config.database.password}",
                "--single-transaction",
                "--routines",
                "--triggers",
                self.config.database.database,
            ]

            # Execute backup
            with open(backup_path, 'w') as backup_file:
                subprocess.run(cmd, stdout=backup_file, check=True)

            logger.info(f"Database backup created: {backup_path}")

        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            raise

    def restore_backup(self, backup_path: str) -> None:
        """Restore database from backup."""
        try:
            import subprocess

            # Build mysql restore command
            cmd = [
                "mysql",
                "-h", self.config.database.host,
                "-P", str(self.config.database.port),
                "-u", self.config.database.username,
                f"-p{self.config.database.password}",
                self.config.database.database,
            ]

            # Execute restore
            with open(backup_path, 'r') as backup_file:
                subprocess.run(cmd, stdin=backup_file, check=True)

            logger.info(f"Database restored from backup: {backup_path}")

        except Exception as e:
            logger.error(f"Failed to restore database backup: {e}")
            raise

    def close(self) -> None:
        """Close database connections."""
        try:
            if self._engine:
                self._engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: Optional[Config] = None) -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config)
    return _db_manager


def close_db_manager() -> None:
    """Close global database manager."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None
