from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from datetime import datetime
import logging

from benchmark_analyzer.db.connector import DatabaseManager
from benchmark_analyzer.db.models import (
    TestRun, TestType, Environment, HardwareBOM, SoftwareBOM,
    ResultsMemoryBandwidth, ResultsCpuLatency
)

logger = logging.getLogger(__name__)

class DataLoader:
    """Handles loading validated data into the database."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def load_results(
        self,
        data: Dict[str, Any],
        test_type: str,
        environment_path: Path,
        bom_path: Optional[Path] = None
    ) -> int:
        """
        Load test results into the database.

        Returns:
            int: The test_run_id of the created test run
        """
        with self.db_manager.get_session() as session:
            # Load environment
            environment = self._load_environment(session, environment_path)

            # Load BOMs if provided
            hw_bom = None
            sw_bom = None
            if bom_path:
                hw_bom, sw_bom = self._load_boms(session, bom_path)

            # Create or get test type
            test_type_obj = self._get_or_create_test_type(session, test_type)

            # Create test run
            test_run = TestRun(
                test_type=test_type_obj,
                environment=environment,
                hw_bom=hw_bom,
                sw_bom=sw_bom,
                engineer=self._get_current_user(),
                created_at=datetime.utcnow(),
                configuration=data.get("configuration", {})
            )
            session.add(test_run)
            session.flush()  # Get the test_run_id

            # Load results based on test type
            self._load_type_specific_results(
                session, test_run.test_run_id, test_type, data["results"]
            )

            return test_run.test_run_id

    def _load_environment(self, session, environment_path: Path) -> Environment:
        """Load environment from YAML file."""
        with open(environment_path) as f:
            env_data = yaml.safe_load(f)

        environment = session.query(Environment).filter_by(
            name=env_data["name"]
        ).first()

        if not environment:
            environment = Environment(
                name=env_data["name"],
                type=env_data["type"],
                comments=env_data.get("comments"),
                tools=env_data.get("tools", {}),
                env_metadata=env_data.get("metadata", {})  # Changed from metadata to env_metadata
            )
            session.add(environment)

        return environment

    def _load_boms(self, session, bom_path: Path) -> tuple[HardwareBOM, SoftwareBOM]:
        """Load hardware and software BOMs from YAML file."""
        with open(bom_path) as f:
            bom_data = yaml.safe_load(f)

        hw_bom = HardwareBOM(
            name=bom_data["hardware"]["name"],
            version=bom_data["hardware"]["version"],
            specs=bom_data["hardware"]["specs"]
        )
        sw_bom = SoftwareBOM(
            name=bom_data["software"]["name"],
            version=bom_data["software"]["version"],
            specs=bom_data["software"]["specs"]
        )

        session.add(hw_bom)
        session.add(sw_bom)
        return hw_bom, sw_bom

    def _get_or_create_test_type(self, session, test_type: str) -> TestType:
        """Get existing test type or create new one."""
        test_type_obj = session.query(TestType).filter_by(
            test_type=test_type
        ).first()

        if not test_type_obj:
            test_type_obj = TestType(
                test_type=test_type,
                schema_version="1.0"  # You might want to make this configurable
            )
            session.add(test_type_obj)

        return test_type_obj

    def _load_type_specific_results(
        self,
        session,
        test_run_id: int,
        test_type: str,
        results: list[Dict[str, Any]]
    ):
        """Load results into the appropriate table based on test type."""
        for result in results:
            if test_type == "memory_bandwidth":
                db_result = ResultsMemoryBandwidth(
                    test_run_id=test_run_id,
                    test_name=result["test_name"],
                    read_bw=result["read_bw"],
                    write_bw=result["write_bw"],
                    timestamp=datetime.fromisoformat(result["timestamp"])
                )
            elif test_type == "cpu_latency":
                db_result = ResultsCpuLatency(
                    test_run_id=test_run_id,
                    test_name=result["test_name"],
                    average_ns=result["average_ns"],
                    latencies_ns=result["latencies_ns"],
                    timestamp=datetime.fromisoformat(result["timestamp"])
                )
            else:
                raise ValueError(f"Unsupported test type: {test_type}")

            session.add(db_result)

    def _get_current_user(self) -> str:
        """Get current user from environment or config."""
        import getpass
        return getpass.getuser()
