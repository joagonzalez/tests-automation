# benchmark_analyzer/cli/main.py
import typer
from typing import Optional
from pathlib import Path
import logging
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from benchmark_analyzer.core.parser import ParserRegistry
from benchmark_analyzer.core.loader import DataLoader
from benchmark_analyzer.core.validator import SchemaValidator
from benchmark_analyzer.db.connector import DatabaseManager
from benchmark_analyzer.config import Config

# Create multiple typer apps for command grouping
app = typer.Typer(
    name="benchmark-analyzer",
    help="CLI tool for analyzing benchmark results"
)
db_app = typer.Typer(help="Database management commands")
app.add_typer(db_app, name="db", help="Database management commands")

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database connection and ensure tables exist."""
    try:
        config = Config()
        db_manager = DatabaseManager(config.db_url)
        db_manager.initialize_tables()
        return db_manager
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise typer.Exit(1)

@app.callback()
def callback():
    """
    Benchmark Analyzer CLI - Tool for processing and analyzing benchmark results.
    """
    # This runs before any command
    try:
        init_database()
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise typer.Exit(1)

@db_app.command("init")
def init_db():
    """Initialize the database and create all tables."""
    try:
        db_manager = init_database()
        rprint("[green]✓[/green] Database initialized successfully")
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to initialize database: {e}")
        raise typer.Exit(1)

@db_app.command("status")
def db_status():
    """Show database status and tables."""
    try:
        db_manager = DatabaseManager()

        # Create a table for display
        table = Table(title="Database Status")
        table.add_column("Table Name", style="cyan")
        table.add_column("Row Count", justify="right", style="green")

        with db_manager.get_session() as session:
            for table_name in db_manager.get_all_tables():
                count = session.execute(f"SELECT COUNT(*) FROM {table_name}").scalar()
                table.add_row(table_name, str(count))

        console.print(table)
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to get database status: {e}")
        raise typer.Exit(1)

@db_app.command("clean")
def clean_db(
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
            raise typer.Exit()

    try:
        db_manager = DatabaseManager()
        db_manager.clean_database()
        rprint("[green]✓[/green] Database cleaned successfully")
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to clean database: {e}")
        raise typer.Exit(1)

@app.command("import")
def import_results(
    package: Path = typer.Option(..., "--package", help="Path to results zip file"),
    test_type: str = typer.Option(..., "--type", help="Test type identifier"),
    bom: Optional[Path] = typer.Option(None, "--bom", help="Path to BOM YAML file"),
    environment: Path = typer.Option(..., "--environment", help="Path to environment YAML file")
):
    """Import test results from a zip package into the database."""
    try:
        # Initialize components
        db_manager = DatabaseManager()
        parser = ParserRegistry.get_parser(test_type)
        validator = SchemaValidator(test_type)
        loader = DataLoader(db_manager)

        with console.status("[bold green]Processing import...") as status:
            # Process the import
            status.update("Parsing package...")
            parsed_data = parser.parse_package(package)

            status.update("Validating data...")
            validator.validate(parsed_data)

            status.update("Loading results...")
            test_run_id = loader.load_results(parsed_data, test_type, environment, bom)

            rprint(f"[green]✓[/green] Successfully imported results (Test Run ID: {test_run_id})")
    except Exception as e:
        rprint(f"[red]✗[/red] Error importing results: {str(e)}")
        raise typer.Exit(1)

@app.command()
def list_test_types():
    """List available test types and their schemas."""
    test_types = ParserRegistry.get_available_test_types()

    table = Table(title="Available Test Types")
    table.add_column("Test Type", style="cyan")
    table.add_column("Schema Path", style="green")

    for test_type in test_types:
        schema_path = f"contracts/tests/{test_type}/schema.json"
        table.add_row(test_type, schema_path)

    console.print(table)

@app.command()
def dashboard():
    """Launch the Streamlit dashboard."""
    try:
        import streamlit.cli as stcli
        import sys

        # Get the path to the dashboard script
        dashboard_path = Path(__file__).parent.parent / "dashboards" / "streamlit_app.py"

        # Run Streamlit
        sys.argv = ["streamlit", "run", str(dashboard_path)]
        stcli.main()
    except ImportError:
        rprint("[red]✗[/red] Streamlit is not installed. Install it with: pip install streamlit")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to launch dashboard: {e}")
        raise typer.Exit(1)

# Add to DatabaseManager class in db/connector.py:
def get_all_tables(self) -> list[str]:
    """Get list of all tables in the database."""
    from sqlalchemy import inspect
    inspector = inspect(self.engine)
    return inspector.get_table_names()

def clean_database(self):
    """Remove all data from all tables."""
    from .models import Base
    Base.metadata.drop_all(self.engine)
    Base.metadata.create_all(self.engine)

if __name__ == "__main__":
    app()
