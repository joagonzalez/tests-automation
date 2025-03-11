from typing import Dict, Any, List
import sqlalchemy as sa
from datetime import datetime
import json
from pathlib import Path
from sqlalchemy import inspect 

class DynamicSchemaManager:
    """Manages dynamic table creation based on test result schemas"""
    
    def __init__(self, db_url: str, schema_dir: Path, metadata: sa.MetaData):
        self.engine = sa.create_engine(db_url)
        self.metadata = metadata
        self.schema_dir = schema_dir
        self.tables: Dict[str, sa.Table] = {}
        
    def _json_type_to_sql(self, json_type: str, is_nullable: bool = True) -> sa.types.TypeEngine:
        """Convert JSON schema types to SQLAlchemy types"""
        type_mapping = {
            'string': sa.String,
            'integer': sa.Integer,
            'number': sa.Float,
            'boolean': sa.Boolean,
            'object': sa.JSON,
            'array': sa.JSON,
            'datetime': sa.DateTime
        }
        sql_type = type_mapping.get(json_type, sa.String)
        return sql_type()

    def _create_columns_from_properties(self, properties: Dict[str, Any], prefix: str = "") -> List[sa.Column]:
        """Recursively create columns from schema properties"""
        columns = []
        
        for prop_name, prop_def in properties.items():
            column_name = f"{prefix}{prop_name}" if prefix else prop_name
            
            if prop_def.get("type") == "object":
                # Recursively handle nested objects
                nested_columns = self._create_columns_from_properties(
                    prop_def["properties"], 
                    f"{column_name}_"
                )
                columns.extend(nested_columns)
            else:
                sql_type = self._json_type_to_sql(prop_def["type"])
                description = prop_def.get("description", "")
                columns.append(
                    sa.Column(
                        column_name, 
                        sql_type,
                        comment=description
                    )
                )
        
        return columns

    def _create_table_from_schema(self, test_type: str, schema: Dict[str, Any]) -> sa.Table:
        """Create SQLAlchemy Table definition from JSON schema"""
        columns = [
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('test_run_id', sa.Integer, sa.ForeignKey('test_runs.id')),
            sa.Column('created_at', sa.DateTime, default=datetime.utcnow)
        ]

        # Add columns based on schema properties
        metric_columns = self._create_columns_from_properties(schema["properties"])
        columns.extend(metric_columns)

        # Create table
        table_name = f"test_results_{test_type}"
        return sa.Table(table_name, self.metadata, *columns)

    def load_schema(self, test_type: str) -> None:
        """Load schema for a test type and create/update corresponding table"""
        schema_file = self.schema_dir / f"{test_type}_schema.json"
        if not schema_file.exists():
            raise ValueError(f"No schema found for test type: {test_type}")

        with open(schema_file) as f:
            schema = json.load(f)

        # Create or update table
        table = self._create_table_from_schema(test_type, schema)
        self.tables[test_type] = table

        # Create table in database if it doesn't exist
        inspector = inspect(self.engine)
        if not inspector.has_table(table.name):
            table.create(self.engine)

class TestResultsDB:
    """Dynamic database manager for test results"""
    
    def __init__(self, db_url: str, schema_dir: Path):
        self.engine = sa.create_engine(db_url)
        self.metadata = sa.MetaData()
        
        # Initialize core tables first
        self._init_core_tables()
        
        # Now initialize schema manager with the same metadata
        self.schema_manager = DynamicSchemaManager(db_url, schema_dir, self.metadata)  # Pass metadata here

    def _init_core_tables(self):
        """Initialize core tables that exist for all test types"""
        self.test_runs = sa.Table(
            'test_runs', self.metadata,
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('test_id', sa.String, nullable=False),
            sa.Column('test_type', sa.String, nullable=False),
            sa.Column('environment', sa.String, nullable=False),
            sa.Column('timestamp', sa.DateTime, nullable=False),
            sa.Column('created_at', sa.DateTime, default=datetime.utcnow)
        )

        # Create all tables in the metadata
        self.metadata.create_all(self.engine)

    def _flatten_metrics(self, metrics: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested metrics structure"""
        flattened = {}
        
        for key, value in metrics.items():
            if isinstance(value, dict):
                nested = self._flatten_metrics(value, f"{prefix}{key}_")
                flattened.update(nested)
            else:
                flattened[f"{prefix}{key}"] = value
        
        return flattened

    def store_results(self, results: Dict[str, Any]) -> bool:
        """Store test results in appropriate table"""
        try:
            test_type = results['metadata']['test_type']
            
            # Ensure schema is loaded
            if test_type not in self.schema_manager.tables:
                self.schema_manager.load_schema(test_type)

            with self.engine.begin() as conn:
                # Convert timestamp string to datetime object
                timestamp = datetime.fromisoformat(
                    results['metadata']['timestamp'].replace('Z', '+00:00')
                )

                # Insert test run
                test_run = conn.execute(
                    self.test_runs.insert().values(
                        test_id=results['metadata']['test_id'],
                        test_type=test_type,
                        environment=results['metadata']['environment'],
                        timestamp=timestamp  # Use the converted timestamp
                    )
                ).inserted_primary_key[0]

                # Flatten and insert test results
                results_table = self.schema_manager.tables[test_type]
                flattened_metrics = self._flatten_metrics(results['benchmark_results'])
                result_data = {
                    'test_run_id': test_run,
                    **flattened_metrics
                }
                conn.execute(results_table.insert().values(**result_data))

            return True
        except Exception as e:
            print(f"Error storing results: {e}")
            return False

    def query_results(self, test_type: str, metrics: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Query results for specific test type and metrics"""
        if test_type not in self.schema_manager.tables:
            self.schema_manager.load_schema(test_type)

        results_table = self.schema_manager.tables[test_type]
        
        # Build dynamic select
        columns = [
            self.test_runs.c.test_id,
            self.test_runs.c.timestamp,
            self.test_runs.c.environment
        ]
        columns.extend(getattr(results_table.c, metric) for metric in metrics)

        query = sa.select(*columns)\
            .join(results_table, results_table.c.test_run_id == self.test_runs.c.id)\
            .order_by(self.test_runs.c.timestamp.desc())\
            .limit(limit)

        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [dict(row) for row in result]
        
    def query_results_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of recent results across all test types"""
        query = sa.select(
            self.test_runs.c.test_id,
            self.test_runs.c.timestamp,
            self.test_runs.c.test_type,
            self.test_runs.c.environment,
            sa.literal('completed').label('status')
        ).order_by(self.test_runs.c.timestamp.desc()).limit(limit)

        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [
                {
                    "test_id": row.test_id,
                    "timestamp": row.timestamp,
                    "test_type": row.test_type,
                    "environment": row.environment,
                    "status": row.status
                }
                for row in result
            ]
        
    def get_available_metrics(self, test_type: str) -> List[Dict[str, Any]]:
        """Get available metrics for a test type"""
        if test_type not in self.schema_manager.tables:
            self.schema_manager.load_schema(test_type)
            
        table = self.schema_manager.tables[test_type]
        return [
            {
                "name": column.name,
                "type": str(column.type),
                "description": getattr(column, 'description', None)
            }
            for column in table.columns
            if column.name not in ['id', 'test_run_id', 'created_at']
        ]