import typer
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.table import Table

from .database.dynamic_schema import TestResultsDB
from .utils.validation import ResultsValidator
from .schemas import get_schema



ARTIFACTS_DIR = Path("artifacts")
DEFAULT_DB_PATH = ARTIFACTS_DIR / "benchmark_results.db"

app = typer.Typer(
    name="benchmark-analyzer",
    help="Analyze infrastructure benchmark results",
)
console = Console()

@app.command()
def import_results(
    results_file: Path = typer.Argument(..., help="Path to results YAML file"),
    environment: Path = typer.Option(..., help="Path to environment configuration YAML"),
    db_path: str = typer.Option(
        str(DEFAULT_DB_PATH), 
        help="SQLite database path"
    ),
    schema_dir: Path = typer.Option("schemas", help="Directory containing test type schemas")
):
    """Import test results from a YAML file"""
    try:
        # Validate environment config
        env_config = ResultsValidator.validate_environment_config(environment)
        console.print(f"[green]Environment configuration validated: {env_config['name']}[/green]")

        # Make sure schema directory exists
        schema_dir.mkdir(exist_ok=True)

        # Read results
        with open(results_file) as f:
            results = yaml.safe_load(f)
            test_type = results['metadata']['test_type']

        # Get and validate against schema
        try:
            schema = get_schema(test_type)
            ResultsValidator.validate_benchmark_results(results, schema)
            console.print(f"[green]Results validated successfully for type: {test_type}[/green]")

            # Create database schema file focusing on benchmark_results structure
            db_schema = {
                "type": "object",
                "properties": schema["properties"]["benchmark_results"]["properties"]
            }

            # Save schema to schema_dir for DynamicSchemaManager
            schema_file = schema_dir / f"{test_type}_schema.json"
            if not schema_file.exists():
                with open(schema_file, 'w') as f:
                    json.dump(db_schema, f, indent=2)
                console.print(f"[green]Schema saved to: {schema_file}[/green]")

        except ValueError as e:
            console.print(f"[red]Schema validation error: {e}[/red]")
            raise typer.Exit(code=1)

        # Initialize database with dynamic schema support
        db = TestResultsDB(f"sqlite:///{db_path}", schema_dir)

        # Store results
        if db.store_results(results):
            console.print("[green]Results imported successfully![/green]")
        else:
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def list_results(
    environment: Path = typer.Option(..., help="Path to environment configuration YAML"),
    test_type: str = typer.Option(None, help="Filter by test type"),
    metrics: list[str] = typer.Option(None, help="Specific metrics to display"),
    limit: int = typer.Option(10, help="Number of results to show"),
    db_path: str = typer.Option(
        str(DEFAULT_DB_PATH), 
        help="SQLite database path"
    ),
    schema_dir: Path = typer.Option("schemas", help="Directory containing test type schemas")
):
    """List imported test results"""
    try:
        # Validate environment config
        env_config = ResultsValidator.validate_environment_config(environment)
        
        # Initialize database with dynamic schema support
        db = TestResultsDB(f"sqlite:///{db_path}", schema_dir)

        # Query results
        if test_type and metrics:
            results = db.query_results(test_type, metrics, limit)
            
            # Create table for display
            table = Table("Test ID", "Timestamp", "Environment", *metrics)
            
            for row in results:
                table.add_row(
                    row['test_id'],
                    row['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                    row['environment'],
                    *[str(row[metric]) for metric in metrics]
                )
        else:
            # Get all test types and their latest results
            results = db.query_results_summary(limit)
            
            table = Table("Test ID", "Timestamp", "Type", "Environment", "Status")
            
            for row in results:
                table.add_row(
                    row['test_id'],
                    row['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                    row['test_type'],
                    row['environment'],
                    row.get('status', 'N/A')
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def list_metrics(
    test_type: str = typer.Argument(..., help="Test type to list metrics for"),
    db_path: str = typer.Option(
        str(DEFAULT_DB_PATH), 
        help="SQLite database path"
    ),
    schema_dir: Path = typer.Option("schemas", help="Directory containing test type schemas")
):
    """List available metrics for a test type"""
    try:
        db = TestResultsDB(f"sqlite:///{db_path}", schema_dir)
        metrics = db.get_available_metrics(test_type)
        
        table = Table("Metric Name", "Type", "Description")
        for metric in metrics:
            table.add_row(
                metric['name'],
                metric['type'],
                metric.get('description', 'N/A')
            )
            
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def dashboard(
    db_path: str = typer.Option(
        str(DEFAULT_DB_PATH),
        help="SQLite database path"
    ),
    port: int = typer.Option(8501, help="Port to run the dashboard on")
):
    """Launch the benchmark analysis dashboard"""
    try:
        # Verify database exists
        db_path = Path(db_path).resolve()
        if not db_path.exists():
            console.print(f"[red]Database not found: {db_path}[/red]")
            raise typer.Exit(code=1)

        # Launch Streamlit
        dashboard_path = Path(__file__).parent / "dashboard" / "main.py"
        
        # Construct Streamlit command
        streamlit_cmd = [
            "streamlit", "run",
            str(dashboard_path),
            "--server.port", str(port),
            "--",  # Separates Streamlit args from script args
            "--db-path", str(db_path)
        ]

        console.print(f"[green]Launching dashboard at http://localhost:{port}[/green]")
        subprocess.run(streamlit_cmd)

    except Exception as e:
        console.print(f"[red]Error launching dashboard: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()