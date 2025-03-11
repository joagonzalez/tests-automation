from pathlib import Path
from typing import Dict

SCHEMAS: Dict[str, dict] = {}

def load_schemas():
    """Load all schema files from the schemas directory"""
    schema_dir = Path(__file__).parent
    for schema_file in schema_dir.glob("*_schema.py"):
        test_type = schema_file.stem.replace("_schema", "")
        module = __import__(f"src.schemas.{schema_file.stem}", fromlist=["SCHEMA"])
        SCHEMAS[test_type] = module.SCHEMA

def get_schema(test_type: str) -> dict:
    """Get schema for a specific test type"""
    if not SCHEMAS:
        load_schemas()
    if test_type not in SCHEMAS:
        raise ValueError(f"No schema found for test type: {test_type}")
    return SCHEMAS[test_type]