# core/criteria.py
from typing import Dict, Any, List
from benchmark_analyzer.db.connector import DatabaseManager
from benchmark_analyzer.db.models import AcceptanceCriteria
import logging

logger = logging.getLogger(__name__)

class CriteriaChecker:
    """Checks test results against acceptance criteria."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def check_results(self, test_run_id: int, test_type: str) -> List[Dict[str, Any]]:
        """
        Check test results against acceptance criteria.

        Returns:
            List of failed criteria checks with details
        """
        with self.db_manager.get_session() as session:
            # Get criteria for test type
            criteria = session.query(AcceptanceCriteria).join(
                AcceptanceCriteria.test_type
            ).filter_by(test_type=test_type).all()

            failures = []
            for criterion in criteria:
                # Build and execute dynamic query
                query = self._build_criteria_query(
                    test_run_id,
                    test_type,
                    criterion
                )
                result = session.execute(query).fetchall()

                if result:
                    failures.append({
                        "metric": criterion.metric,
                        "threshold": criterion.threshold,
                        "operator": criterion.operator,
                        "actual_values": [row[criterion.metric] for row in result],
                        "component": criterion.target_component
                    })

            return failures

    def _build_criteria_query(
        self,
        test_run_id: int,
        test_type: str,
        criterion: AcceptanceCriteria
    ) -> str:
        """Build SQL query for checking a specific criterion."""
        operators = {
            ">": ">",
            "<": "<",
            ">=": ">=",
            "<=": "<=",
            "=": "=",
            "!=": "!="
        }

        table_name = f"results_{test_type}"
        operator = operators.get(criterion.operator)
        if not operator:
            raise ValueError(f"Invalid operator: {criterion.operator}")

        return f"""
            SELECT {criterion.metric}
            FROM {table_name}
            WHERE test_run_id = {test_run_id}
            AND {criterion.metric} {operator} {criterion.threshold}
        """
