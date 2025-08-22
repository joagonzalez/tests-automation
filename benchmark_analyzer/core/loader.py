"""Data loader for importing test results into database."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..config import Config, get_config
from ..db.connector import DatabaseManager, get_db_manager
from ..db.models import (
    Environment,
    HardwareBOM,
    SoftwareBOM,
    TestType,
    TestRun,
    ResultsCpuMem,
    calculate_specs_hash,
)

logger = logging.getLogger(__name__)


class LoaderError(Exception):
    """Exception raised when loading fails."""
    pass


class DataLoader:
    """Data loader for importing test results into database."""

    def __init__(self, config: Optional[Config] = None, db_manager: Optional[DatabaseManager] = None):
        """Initialize data loader."""
        self.config = config or get_config()
        self.db_manager = db_manager or get_db_manager()

    def load_results(
        self,
        test_type: str,
        results: List[Dict[str, Any]],
        environment_file: Optional[Path] = None,
        bom_file: Optional[Path] = None,
        engineer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> str:
        """Load test results into database."""
        try:
            with self.db_manager.get_session() as session:
                # Get or create test type
                test_type_obj = self._get_or_create_test_type(session, test_type)

                # Load environment if provided
                environment_obj = None
                if environment_file:
                    environment_obj = self._load_environment(session, environment_file)

                # Load BOM if provided
                hw_bom_obj = None
                sw_bom_obj = None
                if bom_file:
                    hw_bom_obj, sw_bom_obj = self._load_bom(session, bom_file)

                # Create test run
                test_run = self._create_test_run(
                    session,
                    test_type_obj,
                    environment_obj,
                    hw_bom_obj,
                    sw_bom_obj,
                    engineer,
                    comments,
                )

                # Load results data
                self._load_test_results(session, test_run, test_type, results)

                logger.info(f"Successfully loaded {len(results)} results for test run {test_run.test_run_id}")
                return test_run.test_run_id

        except Exception as e:
            logger.error(f"Failed to load results: {e}")
            raise LoaderError(f"Failed to load results: {e}")

    def _get_or_create_test_type(self, session: Session, test_type_name: str) -> TestType:
        """Get or create test type."""
        try:
            # Try to find existing test type
            test_type_obj = session.query(TestType).filter_by(name=test_type_name).first()

            if not test_type_obj:
                # Create new test type
                test_type_obj = TestType(
                    test_type_id=str(uuid.uuid4()),
                    name=test_type_name,
                    description=f"Test type for {test_type_name} benchmarks",
                )
                session.add(test_type_obj)
                session.flush()  # Get the ID
                logger.info(f"Created new test type: {test_type_name}")
            else:
                logger.debug(f"Using existing test type: {test_type_name}")

            return test_type_obj

        except Exception as e:
            logger.error(f"Failed to get or create test type {test_type_name}: {e}")
            raise

    def _load_environment(self, session: Session, environment_file: Path) -> Environment:
        """Load environment from YAML file."""
        try:
            with open(environment_file, 'r') as f:
                env_data = yaml.safe_load(f)

            # Check if environment already exists
            env_name = env_data.get('name')
            if env_name:
                existing_env = session.query(Environment).filter_by(name=env_name).first()
                if existing_env:
                    logger.debug(f"Using existing environment: {env_name}")
                    return existing_env

            # Create new environment
            environment = Environment(
                id=str(uuid.uuid4()),
                name=env_data.get('name'),
                type=env_data.get('type'),
                comments=env_data.get('comments'),
                tools=env_data.get('tools'),
                env_metadata=env_data.get('metadata'),
            )

            session.add(environment)
            session.flush()
            logger.info(f"Created new environment: {env_data.get('name')}")

            return environment

        except Exception as e:
            logger.error(f"Error loading test data from {results_file}: {e}")
            raise

    def _find_or_create_hw_bom(self, session: Session, specs: Dict[str, Any]) -> HardwareBOM:
        """Find existing hardware BOM by hash or create new one."""
        try:
            # Calculate hash for the specs
            specs_hash = calculate_specs_hash(specs)

            # Try to find existing BOM by hash
            existing_bom = session.query(HardwareBOM).filter_by(specs_hash=specs_hash).first()

            if existing_bom:
                logger.debug(f"Found existing hardware BOM with hash {specs_hash[:8]}...: {existing_bom.bom_id}")
                return existing_bom

            # Create new BOM if not found
            logger.debug(f"Creating new hardware BOM with hash {specs_hash[:8]}...")
            new_bom = HardwareBOM(
                bom_id=str(uuid.uuid4()),
                specs=specs,
                specs_hash=specs_hash
            )
            session.add(new_bom)
            session.flush()  # Get the ID without committing

            logger.info(f"Created new hardware BOM: {new_bom.bom_id}")
            return new_bom

        except Exception as e:
            logger.error(f"Error finding or creating hardware BOM: {e}")
            raise

    def _find_or_create_sw_bom(self, session: Session, specs: Dict[str, Any]) -> SoftwareBOM:
        """Find existing software BOM by hash or create new one."""
        try:
            # Calculate hash for the specs
            specs_hash = calculate_specs_hash(specs)

            # Try to find existing BOM by hash
            existing_bom = session.query(SoftwareBOM).filter_by(specs_hash=specs_hash).first()

            if existing_bom:
                logger.debug(f"Found existing software BOM with hash {specs_hash[:8]}...: {existing_bom.bom_id}")
                return existing_bom

            # Create new BOM if not found
            logger.debug(f"Creating new software BOM with hash {specs_hash[:8]}...")
            new_bom = SoftwareBOM(
                bom_id=str(uuid.uuid4()),
                specs=specs,
                specs_hash=specs_hash
            )
            session.add(new_bom)
            session.flush()  # Get the ID without committing

            logger.info(f"Created new software BOM: {new_bom.bom_id}")
            return new_bom

        except Exception as e:
            logger.error(f"Error finding or creating software BOM: {e}")
            raise

    def _load_bom(self, session: Session, bom_file: Path) -> tuple[Optional[HardwareBOM], Optional[SoftwareBOM]]:
        """Load BOM from YAML file with deduplication."""
        try:
            with open(bom_file, 'r') as f:
                bom_data = yaml.safe_load(f)

            hw_bom = None
            sw_bom = None

            # Handle hardware BOM if present
            if 'hardware' in bom_data:
                hw_specs = bom_data['hardware']
                hw_bom = self._find_or_create_hw_bom(session, hw_specs)

            # Handle software BOM if present
            if 'software' in bom_data:
                sw_specs = bom_data['software']
                sw_bom = self._find_or_create_sw_bom(session, sw_specs)

            return hw_bom, sw_bom

        except Exception as e:
            logger.error(f"Failed to load BOM from {bom_file}: {e}")
            raise

    def _create_test_run(
        self,
        session: Session,
        test_type: TestType,
        environment: Optional[Environment],
        hw_bom: Optional[HardwareBOM],
        sw_bom: Optional[SoftwareBOM],
        engineer: Optional[str],
        comments: Optional[str],
    ) -> TestRun:
        """Create test run record."""
        try:
            test_run = TestRun(
                test_run_id=str(uuid.uuid4()),
                test_type_id=test_type.test_type_id,
                environment_id=environment.id if environment else None,
                hw_bom_id=hw_bom.bom_id if hw_bom else None,
                sw_bom_id=sw_bom.bom_id if sw_bom else None,
                engineer=engineer,
                comments=comments,
                configuration={}  # Can be extended to store additional config
            )

            session.add(test_run)
            session.flush()
            logger.info(f"Created test run: {test_run.test_run_id}")

            return test_run

        except Exception as e:
            logger.error(f"Failed to create test run: {e}")
            raise

    def _load_test_results(
        self,
        session: Session,
        test_run: TestRun,
        test_type: str,
        results: List[Dict[str, Any]],
    ) -> None:
        """Load test results into appropriate table."""
        try:
            if test_type == "cpu_mem":
                self._load_cpu_mem_results(session, test_run, results)
            else:
                # For other test types, we could dynamically create tables
                # For now, log a warning
                logger.warning(f"No specific loader for test type {test_type}, skipping results")

        except Exception as e:
            logger.error(f"Failed to load test results for {test_type}: {e}")
            raise

    def _load_cpu_mem_results(
        self,
        session: Session,
        test_run: TestRun,
        results: List[Dict[str, Any]],
    ) -> None:
        """Load CPU/Memory results into results_cpu_mem table."""
        try:
            # Aggregate all results into a single record
            aggregated_result = self._aggregate_cpu_mem_results(results)

            cpu_mem_result = ResultsCpuMem(
                test_run_id=test_run.test_run_id,
                memory_idle_latency_ns=aggregated_result.get('memory_idle_latency_ns'),
                memory_peak_injection_bandwidth_mbs=aggregated_result.get('memory_peak_injection_bandwidth_mbs'),
                ramspeed_smp_bandwidth_mbs_add=aggregated_result.get('ramspeed_smp_bandwidth_mbs_add'),
                ramspeed_smp_bandwidth_mbs_copy=aggregated_result.get('ramspeed_smp_bandwidth_mbs_copy'),
                sysbench_ram_memory_bandwidth_mibs=aggregated_result.get('sysbench_ram_memory_bandwidth_mibs'),
                sysbench_ram_memory_test_duration_sec=aggregated_result.get('sysbench_ram_memory_test_duration_sec'),
                sysbench_ram_memory_test_mode=aggregated_result.get('sysbench_ram_memory_test_mode'),
                sysbench_cpu_events_per_second=aggregated_result.get('sysbench_cpu_events_per_second'),
                sysbench_cpu_duration_sec=aggregated_result.get('sysbench_cpu_duration_sec'),
                sysbench_cpu_test_mode=aggregated_result.get('sysbench_cpu_test_mode'),
            )

            session.add(cpu_mem_result)
            logger.debug(f"Added CPU/Memory results for test run {test_run.test_run_id}")

        except Exception as e:
            logger.error(f"Failed to load CPU/Memory results: {e}")
            raise

    def _aggregate_cpu_mem_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple CPU/Memory results into a single record."""
        aggregated = {}

        for result in results:
            for key, value in result.items():
                if key.startswith(('memory_', 'ramspeed_', 'sysbench_')):
                    # For numeric values, take the last one or average if needed
                    if isinstance(value, (int, float)):
                        aggregated[key] = value
                    elif isinstance(value, str):
                        aggregated[key] = value

        return aggregated

    def load_from_package(
        self,
        package_path: Path,
        test_type: str,
        environment_file: Optional[Path] = None,
        bom_file: Optional[Path] = None,
        engineer: Optional[str] = None,
        comments: Optional[str] = None,
    ) -> str:
        """Load results from a package file."""
        try:
            from .parser import ParserRegistry

            # Get parser for test type
            parser = ParserRegistry.get_parser(test_type)

            # Parse the package
            results = parser.parse_package(package_path)

            if not results:
                raise LoaderError(f"No valid results found in package {package_path}")

            # Load results into database
            return self.load_results(
                test_type=test_type,
                results=results,
                environment_file=environment_file,
                bom_file=bom_file,
                engineer=engineer,
                comments=comments,
            )

        except Exception as e:
            logger.error(f"Failed to load package {package_path}: {e}")
            raise LoaderError(f"Failed to load package: {e}")

    def get_test_run_summary(self, test_run_id: str) -> Dict[str, Any]:
        """Get summary of a test run."""
        try:
            with self.db_manager.get_session() as session:
                test_run = session.query(TestRun).filter_by(test_run_id=test_run_id).first()

                if not test_run:
                    raise LoaderError(f"Test run {test_run_id} not found")

                # Build summary
                summary = {
                    'test_run_id': test_run.test_run_id,
                    'test_type': test_run.test_type.name if test_run.test_type else None,
                    'environment': test_run.environment.name if test_run.environment else None,
                    'engineer': test_run.engineer,
                    'created_at': test_run.created_at.isoformat(),
                    'comments': test_run.comments,
                    'has_hw_bom': test_run.hw_bom_id is not None,
                    'has_sw_bom': test_run.sw_bom_id is not None,
                    'has_results': False,
                }

                # Check for results
                if test_run.results_cpu_mem:
                    summary['has_results'] = True
                    summary['result_type'] = 'cpu_mem'

                return summary

        except Exception as e:
            logger.error(f"Failed to get test run summary for {test_run_id}: {e}")
            raise LoaderError(f"Failed to get test run summary: {e}")

    def list_test_runs(
        self,
        test_type: Optional[str] = None,
        environment: Optional[str] = None,
        engineer: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List test runs with optional filtering."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(TestRun)

                # Apply filters
                if test_type:
                    query = query.join(TestType).filter(TestType.name == test_type)

                if environment:
                    query = query.join(Environment).filter(Environment.name == environment)

                if engineer:
                    query = query.filter(TestRun.engineer == engineer)

                # Order by creation time (newest first)
                query = query.order_by(TestRun.created_at.desc())

                # Apply pagination
                query = query.limit(limit).offset(offset)

                # Execute query and build result
                test_runs = query.all()
                results = []

                for test_run in test_runs:
                    summary = {
                        'test_run_id': test_run.test_run_id,
                        'test_type': test_run.test_type.name if test_run.test_type else None,
                        'environment': test_run.environment.name if test_run.environment else None,
                        'engineer': test_run.engineer,
                        'created_at': test_run.created_at.isoformat(),
                        'comments': test_run.comments,
                    }
                    results.append(summary)

                return results

        except Exception as e:
            logger.error(f"Failed to list test runs: {e}")
            raise LoaderError(f"Failed to list test runs: {e}")

    def delete_test_run(self, test_run_id: str) -> bool:
        """Delete a test run and its results."""
        try:
            with self.db_manager.get_session() as session:
                test_run = session.query(TestRun).filter_by(test_run_id=test_run_id).first()

                if not test_run:
                    logger.warning(f"Test run {test_run_id} not found")
                    return False

                # Delete the test run (cascade should handle results)
                session.delete(test_run)
                session.commit()

                logger.info(f"Deleted test run {test_run_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete test run {test_run_id}: {e}")
            raise LoaderError(f"Failed to delete test run: {e}")

    def get_test_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.db_manager.get_session() as session:
                stats = {
                    'total_test_runs': session.query(TestRun).count(),
                    'total_test_types': session.query(TestType).count(),
                    'total_environments': session.query(Environment).count(),
                    'total_hw_boms': session.query(HardwareBOM).count(),
                    'total_sw_boms': session.query(SoftwareBOM).count(),
                    'total_cpu_mem_results': session.query(ResultsCpuMem).count(),
                }

                # Get test runs by type
                test_type_counts = (
                    session.query(TestType.name, session.query(TestRun).filter_by(test_type_id=TestType.test_type_id).count())
                    .all()
                )
                stats['test_runs_by_type'] = {name: count for name, count in test_type_counts}

                return stats

        except Exception as e:
            logger.error(f"Failed to get test statistics: {e}")
            raise LoaderError(f"Failed to get test statistics: {e}")
