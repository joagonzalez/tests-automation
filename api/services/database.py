"""Database service for API operations."""

import logging
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, and_, or_, desc, asc

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import (
    Base, TestRun, TestType, Environment, HardwareBOM, SoftwareBOM,
    ResultsCpuMem, ResultsNetworkPerf, AcceptanceCriteria, Operator, MODEL_REGISTRY
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


class DatabaseService(Generic[T]):
    """Generic database service for CRUD operations."""

    def __init__(self, model_class: Type[T]):
        """Initialize database service with model class."""
        self.model_class = model_class
        self.db_manager = get_db_manager()

    @contextmanager
    def get_session(self):
        """Get database session context manager."""
        with self.db_manager.get_session() as session:
            yield session

    def create(self, session: Session, **kwargs) -> T:
        """Create a new record."""
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error creating {self.model_class.__name__}: {e}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error creating {self.model_class.__name__}: {e}")
            raise

    def get_by_id(self, session: Session, record_id: Any) -> Optional[T]:
        """Get record by ID."""
        try:
            # Get primary key column name
            pk_column = self.model_class.__table__.primary_key.columns.values()[0]
            return session.query(self.model_class).filter(pk_column == record_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model_class.__name__} by ID: {e}")
            raise

    def get_all(
        self,
        session: Session,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        **filters
    ) -> List[T]:
        """Get all records with optional filtering and pagination."""
        try:
            query = session.query(self.model_class)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    column = getattr(self.model_class, key)
                    if isinstance(value, str) and value.startswith('%') and value.endswith('%'):
                        # Use LIKE for string matching
                        query = query.filter(column.ilike(value))
                    else:
                        query = query.filter(column == value)

            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                order_column = getattr(self.model_class, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))

            # Apply pagination
            return query.offset(offset).limit(limit).all()

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all {self.model_class.__name__}: {e}")
            raise

    def count(self, session: Session, **filters) -> int:
        """Count records with optional filtering."""
        try:
            query = session.query(self.model_class)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    column = getattr(self.model_class, key)
                    if isinstance(value, str) and value.startswith('%') and value.endswith('%'):
                        query = query.filter(column.ilike(value))
                    else:
                        query = query.filter(column == value)

            return query.count()

        except SQLAlchemyError as e:
            logger.error(f"Database error counting {self.model_class.__name__}: {e}")
            raise

    def update(self, session: Session, record_id: Any, **kwargs) -> Optional[T]:
        """Update a record."""
        try:
            instance = self.get_by_id(session, record_id)
            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            session.commit()
            session.refresh(instance)
            return instance

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error updating {self.model_class.__name__}: {e}")
            raise
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error updating {self.model_class.__name__}: {e}")
            raise

    def delete(self, session: Session, record_id: Any) -> bool:
        """Delete a record."""
        try:
            instance = self.get_by_id(session, record_id)
            if not instance:
                return False

            session.delete(instance)
            session.commit()
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error deleting {self.model_class.__name__}: {e}")
            raise

    def exists(self, session: Session, **filters) -> bool:
        """Check if record exists with given filters."""
        try:
            query = session.query(self.model_class)

            for key, value in filters.items():
                if hasattr(self.model_class, key) and value is not None:
                    column = getattr(self.model_class, key)
                    query = query.filter(column == value)

            return query.first() is not None

        except SQLAlchemyError as e:
            logger.error(f"Database error checking existence of {self.model_class.__name__}: {e}")
            raise


class TestRunService(DatabaseService[TestRun]):
    """Service for TestRun operations."""

    def __init__(self):
        super().__init__(TestRun)

    def get_with_details(self, session: Session, test_run_id: str) -> Optional[Dict[str, Any]]:
        """Get test run with related details."""
        try:
            result = (
                session.query(TestRun, TestType, Environment, HardwareBOM, SoftwareBOM)
                .join(TestType, TestRun.test_type_id == TestType.test_type_id)
                .outerjoin(Environment, TestRun.environment_id == Environment.id)
                .outerjoin(HardwareBOM, TestRun.hw_bom_id == HardwareBOM.bom_id)
                .outerjoin(SoftwareBOM, TestRun.sw_bom_id == SoftwareBOM.bom_id)
                .filter(TestRun.test_run_id == test_run_id)
                .first()
            )

            if not result:
                return None

            test_run, test_type, environment, hw_bom, sw_bom = result

            return {
                "test_run": test_run,
                "test_type": test_type,
                "environment": environment,
                "hw_bom": hw_bom,
                "sw_bom": sw_bom,
                "has_results": session.query(ResultsCpuMem).filter(
                    ResultsCpuMem.test_run_id == test_run_id
                ).first() is not None
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting test run details: {e}")
            raise

    def get_statistics(self, session: Session) -> Dict[str, Any]:
        """Get test run statistics."""
        try:
            total_runs = session.query(TestRun).count()

            # Runs by test type
            runs_by_type = {}
            type_counts = (
                session.query(TestType.name, func.count(TestRun.test_run_id))
                .join(TestRun)
                .group_by(TestType.name)
                .all()
            )
            for name, count in type_counts:
                runs_by_type[name] = count

            # Runs by engineer
            runs_by_engineer = {}
            engineer_counts = (
                session.query(TestRun.engineer, func.count(TestRun.test_run_id))
                .filter(TestRun.engineer.is_not(None))
                .group_by(TestRun.engineer)
                .all()
            )
            for engineer, count in engineer_counts:
                runs_by_engineer[engineer] = count

            # Recent runs
            recent_runs = (
                session.query(TestRun)
                .order_by(desc(TestRun.created_at))
                .limit(10)
                .all()
            )

            return {
                "total_runs": total_runs,
                "runs_by_type": runs_by_type,
                "runs_by_engineer": runs_by_engineer,
                "recent_runs": recent_runs,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting test run statistics: {e}")
            raise


class TestTypeService(DatabaseService[TestType]):
    """Service for TestType operations."""

    def __init__(self):
        super().__init__(TestType)

    def get_by_name(self, session: Session, name: str) -> Optional[TestType]:
        """Get test type by name."""
        try:
            return session.query(TestType).filter(TestType.name == name).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting test type by name: {e}")
            raise

    def get_with_run_count(self, session: Session, test_type_id: str) -> Optional[Dict[str, Any]]:
        """Get test type with test run count."""
        try:
            test_type = self.get_by_id(session, test_type_id)
            if not test_type:
                return None

            run_count = (
                session.query(TestRun)
                .filter(TestRun.test_type_id == test_type_id)
                .count()
            )

            return {
                "test_type": test_type,
                "run_count": run_count,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting test type with run count: {e}")
            raise


class EnvironmentService(DatabaseService[Environment]):
    """Service for Environment operations."""

    def __init__(self):
        super().__init__(Environment)

    def get_by_name(self, session: Session, name: str) -> Optional[Environment]:
        """Get environment by name."""
        try:
            return session.query(Environment).filter(Environment.name == name).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting environment by name: {e}")
            raise

    def get_statistics(self, session: Session) -> Dict[str, Any]:
        """Get environment statistics."""
        try:
            total_environments = session.query(Environment).count()

            # Environments by type
            environments_by_type = {}
            type_counts = (
                session.query(Environment.type, func.count(Environment.id))
                .filter(Environment.type.is_not(None))
                .group_by(Environment.type)
                .all()
            )
            for env_type, count in type_counts:
                environments_by_type[env_type] = count

            # Environments with tools
            environments_with_tools = (
                session.query(Environment)
                .filter(Environment.tools.is_not(None))
                .filter(Environment.tools != {})
                .count()
            )

            return {
                "total_environments": total_environments,
                "environments_by_type": environments_by_type,
                "environments_with_tools": environments_with_tools,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting environment statistics: {e}")
            raise


class ResultsService(DatabaseService[ResultsCpuMem]):
    """Service for Results operations."""

    def __init__(self):
        super().__init__(ResultsCpuMem)

    def get_with_test_run_details(
        self,
        session: Session,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get results with test run details."""
        try:
            query = (
                session.query(ResultsCpuMem, TestRun, TestType, Environment)
                .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
                .join(TestType, TestRun.test_type_id == TestType.test_type_id)
                .outerjoin(Environment, TestRun.environment_id == Environment.id)
            )

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if key == "test_type" and value:
                        query = query.filter(TestType.name.ilike(f"%{value}%"))
                    elif key == "environment" and value:
                        query = query.filter(Environment.name.ilike(f"%{value}%"))
                    elif key == "engineer" and value:
                        query = query.filter(TestRun.engineer.ilike(f"%{value}%"))
                    elif key == "date_from" and value:
                        query = query.filter(TestRun.created_at >= value)
                    elif key == "date_to" and value:
                        query = query.filter(TestRun.created_at <= value)

            # Apply ordering
            if order_by == "created_at":
                if order_desc:
                    query = query.order_by(desc(TestRun.created_at))
                else:
                    query = query.order_by(asc(TestRun.created_at))

            # Apply pagination
            results = query.offset(offset).limit(limit).all()

            return [
                {
                    "result": result,
                    "test_run": test_run,
                    "test_type": test_type,
                    "environment": environment,
                }
                for result, test_run, test_type, environment in results
            ]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting results with details: {e}")
            raise

    def get_statistics(self, session: Session) -> Dict[str, Any]:
        """Get results statistics."""
        try:
            total_results = session.query(ResultsCpuMem).count()

            # Results by test type
            results_by_test_type = {}
            type_counts = (
                session.query(TestType.name, func.count(ResultsCpuMem.test_run_id))
                .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
                .join(TestType, TestRun.test_type_id == TestType.test_type_id)
                .group_by(TestType.name)
                .all()
            )
            for name, count in type_counts:
                results_by_test_type[name] = count

            # Metric statistics
            metrics_summary = {}

            # Memory metrics
            memory_stats = (
                session.query(
                    func.avg(ResultsCpuMem.memory_idle_latency_ns),
                    func.min(ResultsCpuMem.memory_idle_latency_ns),
                    func.max(ResultsCpuMem.memory_idle_latency_ns),
                )
                .filter(ResultsCpuMem.memory_idle_latency_ns.is_not(None))
                .first()
            )

            if memory_stats[0] is not None:
                metrics_summary["memory_idle_latency_ns"] = {
                    "avg": float(memory_stats[0]),
                    "min": float(memory_stats[1]),
                    "max": float(memory_stats[2]),
                }

            # CPU metrics
            cpu_stats = (
                session.query(
                    func.avg(ResultsCpuMem.sysbench_cpu_events_per_second),
                    func.min(ResultsCpuMem.sysbench_cpu_events_per_second),
                    func.max(ResultsCpuMem.sysbench_cpu_events_per_second),
                )
                .filter(ResultsCpuMem.sysbench_cpu_events_per_second.is_not(None))
                .first()
            )

            if cpu_stats[0] is not None:
                metrics_summary["sysbench_cpu_events_per_second"] = {
                    "avg": float(cpu_stats[0]),
                    "min": float(cpu_stats[1]),
                    "max": float(cpu_stats[2]),
                }

            return {
                "total_results": total_results,
                "results_by_test_type": results_by_test_type,
                "metrics_summary": metrics_summary,
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting results statistics: {e}")
            raise


class DatabaseServiceFactory:
    """Factory for creating database services."""

    _services = {
        "test_runs": TestRunService,
        "test_types": TestTypeService,
        "environments": EnvironmentService,
        "results": ResultsService,
        "hw_bom": lambda: DatabaseService(HardwareBOM),
        "sw_bom": lambda: DatabaseService(SoftwareBOM),
        "acceptance_criteria": lambda: DatabaseService(AcceptanceCriteria),
        "operators": lambda: DatabaseService(Operator),
    }

    @classmethod
    def get_service(cls, service_name: str):
        """Get database service by name."""
        if service_name not in cls._services:
            raise ValueError(f"Unknown service: {service_name}")

        service_class = cls._services[service_name]
        return service_class()

    @classmethod
    def get_available_services(cls) -> List[str]:
        """Get list of available services."""
        return list(cls._services.keys())


# Global service instances
test_run_service = TestRunService()
test_type_service = TestTypeService()
environment_service = EnvironmentService()
results_service = ResultsService()
