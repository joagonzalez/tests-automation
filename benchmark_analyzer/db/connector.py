# db/connector.py
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, db_url: str = "sqlite:///benchmark_results.db"):
        self.engine = create_engine(db_url)
        self.metadata = MetaData()
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator:
        """Provide a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()

    def initialize_tables(self):
        """Create all tables in the database."""
        from .models import Base
        Base.metadata.create_all(self.engine)
