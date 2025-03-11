from typing import List, Dict, Any
import sqlalchemy as sa
from sqlalchemy import create_engine
from datetime import datetime, timedelta

class DashboardQueries:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def get_recent_tests(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        SELECT test_id, timestamp, test_type, environment
        FROM test_runs
        ORDER BY timestamp DESC
        LIMIT :limit
        """
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"limit": limit})
            return [dict(row) for row in result]

    def get_test_types(self) -> List[str]:
        query = "SELECT DISTINCT test_type FROM test_runs"
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query))
            return [row[0] for row in result]

    def get_metrics_for_test_type(self, test_type: str) -> List[Dict[str, Any]]:
        # This query needs to be adapted based on your dynamic schema implementation
        query = f"""
        SELECT column_name 
        FROM pragma_table_info('test_results_{test_type}')
        WHERE column_name NOT IN ('id', 'test_run_id', 'created_at')
        """
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query))
            return [dict(name=row[0]) for row in result]

    def get_metric_data(
        self, 
        test_type: str, 
        metric: str, 
        days: int = 7
    ) -> List[Dict[str, Any]]:
        query = f"""
        SELECT 
            tr.timestamp,
            trt.{metric} as value
        FROM test_runs tr
        JOIN test_results_{test_type} trt ON trt.test_run_id = tr.id
        WHERE tr.timestamp >= :start_date
        ORDER BY tr.timestamp
        """
        start_date = datetime.now() - timedelta(days=days)
        
        with self.engine.connect() as conn:
            result = conn.execute(sa.text(query), {"start_date": start_date})
            return [dict(row) for row in result]