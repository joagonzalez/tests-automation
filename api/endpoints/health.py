"""Health check endpoints for the API."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from benchmark_analyzer.db.connector import get_db_manager
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "benchmark-analyzer-api",
        "version": config["app"]["version"],
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """Detailed health check with dependency status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "benchmark-analyzer-api",
        "version": config["app"]["version"],
        "environment": config["environment"]["name"],
        "checks": {}
    }

    # Check database connection
    try:
        db_manager = get_db_manager()
        db_healthy = db_manager.test_connection()

        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "details": {
                "host": config["database"]["host"],
                "port": config["database"]["port"],
                "database": config["database"]["database"],
                "driver": config["database"]["driver"],
            }
        }

        if db_healthy:
            # Get database statistics
            db_status = db_manager.get_database_status()
            health_status["checks"]["database"]["stats"] = {
                "total_tables": len(db_status.get("tables", {})),
                "total_rows": db_status.get("total_rows", 0),
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check file system (upload directories)
    try:
        import os
        upload_dir = config["upload"]["upload_dir"]
        temp_dir = config["upload"]["temp_dir"]

        upload_dir_exists = os.path.exists(upload_dir)
        temp_dir_exists = os.path.exists(temp_dir)

        health_status["checks"]["filesystem"] = {
            "status": "healthy" if upload_dir_exists and temp_dir_exists else "unhealthy",
            "details": {
                "upload_dir": {
                    "path": upload_dir,
                    "exists": upload_dir_exists,
                    "writable": os.access(upload_dir, os.W_OK) if upload_dir_exists else False
                },
                "temp_dir": {
                    "path": temp_dir,
                    "exists": temp_dir_exists,
                    "writable": os.access(temp_dir, os.W_OK) if temp_dir_exists else False
                }
            }
        }
    except Exception as e:
        logger.error(f"Filesystem health check failed: {e}")
        health_status["checks"]["filesystem"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Overall health status
    all_healthy = all(
        check.get("status") == "healthy"
        for check in health_status["checks"].values()
    )

    if not all_healthy:
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/liveness")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}


@router.get("/readiness")
async def readiness_probe(db: Session = Depends(get_db_session)) -> Dict[str, str]:
    """Kubernetes readiness probe endpoint."""
    try:
        # Test database connection
        db_manager = get_db_manager()
        if not db_manager.test_connection():
            raise HTTPException(status_code=503, detail="Database not ready")

        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Basic metrics endpoint."""
    try:
        db_manager = get_db_manager()
        db_status = db_manager.get_database_status()

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connection_status": "connected" if db_status["connection"] else "disconnected",
                "total_tables": len(db_status.get("tables", {})),
                "total_rows": db_status.get("total_rows", 0),
                "table_counts": db_status.get("tables", {}),
            },
            "application": {
                "version": config["app"]["version"],
                "environment": config["environment"]["name"],
                "debug_mode": config["app"]["debug"],
            }
        }

        return metrics
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")
