"""Main FastAPI application for benchmark analyzer API."""

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Add the benchmark_analyzer module to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_analyzer.config import Config, get_config
from benchmark_analyzer.db.connector import DatabaseManager, get_db_manager
from api.config.settings import config
from api.endpoints import (
    health,
    test_runs,
    test_types,
    environments,
    results,
    upload,
    boms,
)



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url}")

        try:
            response = await call_next(request)

            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} - "
                f"Process time: {process_time:.4f}s"
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - Process time: {process_time:.4f}s"
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up Benchmark Analyzer API...")

    try:
        # Initialize database connection
        db_manager = get_db_manager()

        # Test database connection
        if not db_manager.test_connection():
            logger.error("Failed to connect to database")
            raise RuntimeError("Database connection failed")

        # Initialize database tables if needed
        db_manager.initialize_tables()

        logger.info("Database connection established and tables initialized")

        # Store database manager in app state
        app.state.db_manager = db_manager

        logger.info("API startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Benchmark Analyzer API...")

    try:
        # Close database connections
        if hasattr(app.state, 'db_manager'):
            app.state.db_manager.close()

        logger.info("API shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


class Application:
    """FastAPI application wrapper with configuration management."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize application with configuration."""
        self.config_dict = config_dict or config
        self.app: Optional[FastAPI] = None
        self._setup_app()

    def _setup_app(self) -> None:
        """Set up FastAPI application."""
        app_config = self.config_dict["app"]

        # Create FastAPI app with lifespan
        self.app = FastAPI(
            title=app_config["title"],
            description=app_config["description"],
            version=app_config["version"],
            debug=app_config["debug"],
            docs_url=app_config["docs_url"],
            redoc_url=app_config["redoc_url"],
            openapi_url=app_config["openapi_url"],
            lifespan=lifespan,
        )

        # Add middleware
        self._setup_middleware()

        # Add exception handlers
        self._setup_exception_handlers()

        # Include routers
        self._setup_routes()

        logger.info("FastAPI application configured successfully")

    def _setup_middleware(self) -> None:
        """Set up middleware."""
        cors_config = self.config_dict["cors"]

        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config["allow_origins"],
            allow_credentials=cors_config["allow_credentials"],
            allow_methods=cors_config["allow_methods"],
            allow_headers=cors_config["allow_headers"],
        )

        # Logging middleware
        if not self.config_dict["environment"]["testing"]:
            self.app.add_middleware(LoggingMiddleware)

    def _setup_exception_handlers(self) -> None:
        """Set up exception handlers."""

        @self.app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(request: Request, exc: StarletteHTTPException):
            """Handle HTTP exceptions."""
            logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": True,
                    "message": exc.detail,
                    "status_code": exc.status_code,
                },
            )

        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """Handle validation errors."""
            logger.error(f"Validation error: {exc.errors()}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": True,
                    "message": "Validation error",
                    "details": exc.errors(),
                    "status_code": 422,
                },
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle general exceptions."""
            logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Internal server error",
                    "status_code": 500,
                },
            )

    def _setup_routes(self) -> None:
        """Set up API routes."""
        # Include routers
        self.app.include_router(
            health.router,
            prefix="/health",
            tags=["health"]
        )

        self.app.include_router(
            test_runs.router,
            prefix="/api/v1/test-runs",
            tags=["test-runs"]
        )

        self.app.include_router(
            test_types.router,
            prefix="/api/v1/test-types",
            tags=["test-types"]
        )

        self.app.include_router(
            environments.router,
            prefix="/api/v1/environments",
            tags=["environments"]
        )

        self.app.include_router(
            results.router,
            prefix="/api/v1/results",
            tags=["results"]
        )

        self.app.include_router(
            upload.router,
            prefix="/api/v1/upload",
            tags=["upload"]
        )

        self.app.include_router(
            boms.router,
            prefix="/api/v1/boms",
            tags=["boms"]
        )

        # Root endpoint
        @self.app.get("/", include_in_schema=False)
        async def root():
            """Root endpoint."""
            return {
                "message": "Benchmark Analyzer API",
                "version": self.config_dict["app"]["version"],
                "docs_url": self.config_dict["app"]["docs_url"],
                "status": "running"
            }

        # API info endpoint
        @self.app.get("/api/info")
        async def api_info():
            """API information endpoint."""
            return {
                "title": self.config_dict["app"]["title"],
                "description": self.config_dict["app"]["description"],
                "version": self.config_dict["app"]["version"],
                "environment": self.config_dict["environment"]["name"],
                "debug": self.config_dict["app"]["debug"],
            }

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        if self.app is None:
            raise RuntimeError("Application not initialized")
        return self.app

    def run(self, **kwargs) -> None:
        """Run the application with uvicorn."""
        server_config = self.config_dict["server"]

        # Merge default config with provided kwargs
        uvicorn_config = {
            "app": self.app,
            "host": server_config["host"],
            "port": server_config["port"],
            "log_level": server_config["log_level"],
            "reload": server_config["reload"],
            "workers": server_config["workers"] if not server_config["reload"] else 1,
            **kwargs
        }

        logger.info(f"Starting server on {server_config['host']}:{server_config['port']}")
        uvicorn.run(**uvicorn_config)


def create_app(config_dict: Optional[Dict[str, Any]] = None) -> FastAPI:
    """Create FastAPI application instance."""
    application = Application(config_dict)
    return application.get_app()


# Create module-level app instance for uvicorn
app = create_app()


def main():
    """Main entry point for the API."""
    import time

    try:
        # Create application
        application = Application()

        # Run the application
        application.run()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
