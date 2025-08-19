"""Main CLI interface for benchmark analyzer."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import Config, get_config
from ..core.loader import DataLoader, LoaderError
from ..core.parser import ParserRegistry, ParseError
from ..core.validator import SchemaValidator, ValidationResult
from ..db.connector import DatabaseManager, get_db_manager

# Create the main CLI app
app = typer.Typer(
    name="benchmark-analyzer",
    help="CLI tool for analyzing benchmark results",
    no_args_is_help=True,
)

# Create sub-apps for command grouping
db_app = typer.Typer(help="Database management commands")
query_app = typer.Typer(help="Query and list commands")
schema_app = typer.Typer(help="Schema management commands")

# Add sub-apps to main app
app.add_typer(db_app, name="db")
app.add_typer(query_app, name="query")
app.add_typer(schema_app, name="schema")

# Global console for rich output
console = Console()

# Global state
config: Optional[Config] = None
db_manager: Optional[DatabaseManager] = None


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )

def initialize_app(env_file: Optional[str] = None) -> None:
    """Initialize application components."""
    global config, db_manager

    try:
        # Load configuration
        config = get_config(env_file)

        # Ensure directories exist
        config.ensure_directories()

        # Initialize database manager
        db_manager = get_db_manager(config)

        # Test database connection
        if not db_manager.test_connection():
            rprint("[red]❌ Database connection failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]❌ Failed to initialize application: {e}[/red]")
        raise typer.Exit(1)


@app.callback()
def main(
    env_file: Optional[str] = typer.Option(
        None,
        "--env-file",
        "-e",
        help="Path to environment (.env) file"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    ),
):
    """
    Benchmark Analyzer CLI - Tool for processing and analyzing benchmark results.
    """
    setup_logging(verbose)
    initialize_app(env_file)

@app.command()
def import_results(
    package: Path = typer.Option(
        ...,
        "--package",
        "-p",
        help="Path to results package (ZIP file or directory)",
        exists=True
    ),
    test_type: str = typer.Option(
        ...,
        "--type",
        "-t",
        help="Test type identifier"
    ),
    environment: Optional[Path] = typer.Option(
        None,
        "--environment",
        "-e",
        help="Path to environment YAML file",
        exists=True
    ),
    bom: Optional[Path] = typer.Option(
        None,
        "--bom",
        "-b",
        help="Path to BOM YAML file",
        exists=True
    ),
    engineer: Optional[str] = typer.Option(
        None,
        "--engineer",
        help="Engineer name"
    ),
    comments: Optional[str] = typer.Option(
        None,
        "--comments",
        help="Comments about the test run"
    ),
    validate_only: bool = typer.Option(
        False,
        "--validate-only",
        help="Only validate the data, don't import"
    ),
):
    """Import test results from a package into the database."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Check if test type is supported
            if not ParserRegistry.is_test_type_supported(test_type):
                available_types = ParserRegistry.get_available_test_types()
                rprint(f"[red]❌ Test type '{test_type}' not supported[/red]")
                rprint(f"Available types: {', '.join(available_types)}")
                raise typer.Exit(1)

            # Parse results
            task = progress.add_task("Parsing package...", total=None)
            parser = ParserRegistry.get_parser(test_type, config)
            results = parser.parse_package(package)

            if not results:
                rprint(f"[red]❌ No valid results found in package[/red]")
                raise typer.Exit(1)

            progress.update(task, description=f"Found {len(results)} results")

            # Validate results
            progress.update(task, description="Validating results...")
            validator = SchemaValidator(config)

            validation_errors = []
            for i, result in enumerate(results):
                validation_result = validator.validate_test_results(test_type, result)
                if not validation_result.is_valid:
                    validation_errors.extend([f"Result {i+1}: {error}" for error in validation_result.errors])

            # Validate environment if provided
            if environment:
                env_validation = validator.validate_environment_file(environment)
                if not env_validation.is_valid:
                    validation_errors.extend([f"Environment: {error}" for error in env_validation.errors])

            # Validate BOM if provided
            if bom:
                bom_validation = validator.validate_bom_file(bom, test_type)
                if not bom_validation.is_valid:
                    validation_errors.extend([f"BOM: {error}" for error in bom_validation.errors])

            if validation_errors:
                rprint("[red]❌ Validation failed:[/red]")
                for error in validation_errors:
                    rprint(f"  • {error}")
                raise typer.Exit(1)

            rprint("[green]✅ Validation passed[/green]")

            if validate_only:
                rprint("[blue]ℹ️  Validation-only mode, skipping import[/blue]")
                return

            # Import results
            progress.update(task, description="Importing results...")
            loader = DataLoader(config, db_manager)

            test_run_id = loader.load_results(
                test_type=test_type,
                results=results,
                environment_file=environment,
                bom_file=bom,
                engineer=engineer,
                comments=comments
            )

            progress.update(task, description="Import completed", total=1, completed=1)

        rprint(f"[green]✅ Successfully imported {len(results)} results[/green]")
        rprint(f"[blue]Test Run ID: {test_run_id}[/blue]")

    except (ParseError, LoaderError) as e:
        rprint(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("init")
def init_database():
    """Initialize the database and create all tables."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing database...", total=None)

            db_manager.initialize_tables()

            progress.update(task, description="Database initialized", total=1, completed=1)

        rprint("[green]✅ Database initialized successfully[/green]")

    except Exception as e:
        rprint(f"[red]❌ Failed to initialize database: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("status")
def database_status():
    """Show database status and statistics."""
    try:
        status = db_manager.get_database_status()

        # Connection status
        if status["connection"]:
            rprint("[green]✅ Database connection: OK[/green]")
        else:
            rprint("[red]❌ Database connection: FAILED[/red]")
            if "error" in status:
                rprint(f"Error: {status['error']}")
            return

        # Tables overview
        table = Table(title="Database Tables")
        table.add_column("Table Name", style="cyan")
        table.add_column("Row Count", justify="right", style="green")

        for table_name, count in status["tables"].items():
            if isinstance(count, int):
                table.add_row(table_name, f"{count:,}")
            else:
                table.add_row(table_name, str(count))

        console.print(table)

        # Summary
        if isinstance(status["total_rows"], int):
            rprint(f"\n[blue]Total rows: {status['total_rows']:,}[/blue]")

    except Exception as e:
        rprint(f"[red]❌ Failed to get database status: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("clean")
def clean_database(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force cleanup without confirmation"
    )
):
    """Clean all data from the database."""
    if not force:
        confirm = typer.confirm(
            "⚠️  This will delete all data from the database. Are you sure?"
        )
        if not confirm:
            rprint("[yellow]Operation cancelled[/yellow]")
            return

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cleaning database...", total=None)

            db_manager.clean_database()

            progress.update(task, description="Database cleaned", total=1, completed=1)

        rprint("[green]✅ Database cleaned successfully[/green]")

    except Exception as e:
        rprint(f"[red]❌ Failed to clean database: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("test-runs")
def list_test_runs(
    test_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by test type"
    ),
    environment: Optional[str] = typer.Option(
        None,
        "--environment",
        "-e",
        help="Filter by environment"
    ),
    engineer: Optional[str] = typer.Option(
        None,
        "--engineer",
        help="Filter by engineer"
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Maximum number of results"
    ),
    offset: int = typer.Option(
        0,
        "--offset",
        help="Offset for pagination"
    ),
):
    """List test runs with optional filtering."""
    try:
        loader = DataLoader(config, db_manager)
        test_runs = loader.list_test_runs(
            test_type=test_type,
            environment=environment,
            engineer=engineer,
            limit=limit,
            offset=offset
        )

        if not test_runs:
            rprint("[yellow]No test runs found[/yellow]")
            return

        # Create table
        table = Table(title="Test Runs")
        table.add_column("Test Run ID", style="cyan")
        table.add_column("Test Type", style="green")
        table.add_column("Environment", style="blue")
        table.add_column("Engineer", style="magenta")
        table.add_column("Created", style="yellow")

        for run in test_runs:
            table.add_row(
                run["test_run_id"][:8] + "...",  # Truncate ID
                run["test_type"] or "N/A",
                run["environment"] or "N/A",
                run["engineer"] or "N/A",
                run["created_at"][:19]  # Remove microseconds
            )

        console.print(table)

        if len(test_runs) == limit:
            rprint(f"\n[blue]Showing {len(test_runs)} results (use --offset to see more)[/blue]")

    except Exception as e:
        rprint(f"[red]❌ Failed to list test runs: {e}[/red]")
        raise typer.Exit(1)


@query_app.command("test-types")
def list_test_types():
    """List available test types."""
    try:
        # Get registered test types
        registered_types = ParserRegistry.get_available_test_types()

        # Get schema validator
        validator = SchemaValidator(config)
        schema_types = validator.get_supported_test_types()

        table = Table(title="Test Types")
        table.add_column("Test Type", style="cyan")
        table.add_column("Parser", style="green")
        table.add_column("Schema", style="blue")
        table.add_column("Description", style="yellow")

        all_types = set(registered_types + schema_types)

        for test_type in sorted(all_types):
            has_parser = "✅" if test_type in registered_types else "❌"
            has_schema = "✅" if test_type in schema_types else "❌"

            # Get parser info if available
            description = "N/A"
            if test_type in registered_types:
                try:
                    parser_info = ParserRegistry.get_parser_info(test_type)
                    description = parser_info.get("class_name", "N/A")
                except Exception:
                    pass

            table.add_row(test_type, has_parser, has_schema, description)

        console.print(table)

    except Exception as e:
        rprint(f"[red]❌ Failed to list test types: {e}[/red]")
        raise typer.Exit(1)

@schema_app.command("validate")
def validate_schema(
    schema_file: Path = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Path to schema file",
        exists=True
    ),
    data_file: Path = typer.Option(
        ...,
        "--data",
        "-d",
        help="Path to data file to validate",
        exists=True
    ),
):
    """Validate a data file against a schema."""
    try:
        import json
        import yaml

        # Load schema
        with open(schema_file, 'r') as f:
            schema = json.load(f)

        # Load data
        with open(data_file, 'r') as f:
            if data_file.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Validate
        from ..core.validator import JSONSchemaValidator
        validator = JSONSchemaValidator(schema)
        result = validator.validate(data)

        if result.is_valid:
            rprint("[green]✅ Validation passed[/green]")
        else:
            rprint("[red]❌ Validation failed:[/red]")
            for error in result.errors:
                rprint(f"  • {error}")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]❌ Validation error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config_info():
    """Show current configuration."""
    try:
        config_dict = config.to_dict()

        table = Table(title="Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        def add_config_section(section_name: str, section_data: dict, prefix: str = ""):
            for key, value in section_data.items():
                full_key = f"{prefix}{key}" if prefix else key

                if isinstance(value, dict):
                    add_config_section(section_name, value, f"{full_key}.")
                else:
                    table.add_row(f"{section_name}.{full_key}", str(value))

        for section_name, section_data in config_dict.items():
            if isinstance(section_data, dict):
                add_config_section(section_name, section_data)
            else:
                table.add_row(section_name, str(section_data))

        console.print(table)

    except Exception as e:
        rprint(f"[red]❌ Failed to show configuration: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
