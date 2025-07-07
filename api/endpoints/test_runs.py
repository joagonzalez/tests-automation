"""Test runs API endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import TestRun, TestType, Environment, HardwareBOM, SoftwareBOM
from benchmark_analyzer.core.loader import DataLoader
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class TestRunBase(BaseModel):
    """Base test run model."""
    test_type_id: str
    environment_id: Optional[str] = None
    hw_bom_id: Optional[str] = None
    sw_bom_id: Optional[str] = None
    engineer: Optional[str] = None
    comments: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class TestRunCreate(TestRunBase):
    """Test run creation model."""
    pass


class TestRunUpdate(BaseModel):
    """Test run update model."""
    engineer: Optional[str] = None
    comments: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class TestRunResponse(TestRunBase):
    """Test run response model."""
    test_run_id: str
    created_at: datetime
    test_type_name: Optional[str] = None
    environment_name: Optional[str] = None
    has_results: bool = False

    class Config:
        from_attributes = True


class TestRunListResponse(BaseModel):
    """Test run list response model."""
    items: List[TestRunResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class TestRunStats(BaseModel):
    """Test run statistics model."""
    total_runs: int
    runs_by_type: Dict[str, int]
    runs_by_engineer: Dict[str, int]
    recent_runs: List[TestRunResponse]


@router.get("/", response_model=TestRunListResponse)
async def list_test_runs(
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    test_type: Optional[str] = Query(None, description="Filter by test type"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    engineer: Optional[str] = Query(None, description="Filter by engineer"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
) -> TestRunListResponse:
    """List test runs with filtering and pagination."""
    try:
        # Build query
        query = db.query(TestRun)

        # Apply filters
        if test_type:
            query = query.join(TestType).filter(TestType.name == test_type)

        if environment:
            query = query.join(Environment).filter(Environment.name == environment)

        if engineer:
            query = query.filter(TestRun.engineer == engineer)

        # Apply sorting
        if sort_by == "created_at":
            if sort_order == "desc":
                query = query.order_by(TestRun.created_at.desc())
            else:
                query = query.order_by(TestRun.created_at.asc())

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        test_runs = query.offset(offset).limit(page_size).all()

        # Convert to response models
        items = []
        for run in test_runs:
            item = TestRunResponse(
                test_run_id=run.test_run_id,
                test_type_id=run.test_type_id,
                environment_id=run.environment_id,
                hw_bom_id=run.hw_bom_id,
                sw_bom_id=run.sw_bom_id,
                engineer=run.engineer,
                comments=run.comments,
                configuration=run.configuration,
                created_at=run.created_at,
                test_type_name=run.test_type.name if run.test_type else None,
                environment_name=run.environment.name if run.environment else None,
                has_results=run.results_cpu_mem is not None,
            )
            items.append(item)

        return TestRunListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list test runs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list test runs")


@router.get("/{test_run_id}", response_model=TestRunResponse)
async def get_test_run(
    test_run_id: str,
    db: Session = Depends(get_db_session),
) -> TestRunResponse:
    """Get a specific test run."""
    try:
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()

        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        return TestRunResponse(
            test_run_id=test_run.test_run_id,
            test_type_id=test_run.test_type_id,
            environment_id=test_run.environment_id,
            hw_bom_id=test_run.hw_bom_id,
            sw_bom_id=test_run.sw_bom_id,
            engineer=test_run.engineer,
            comments=test_run.comments,
            configuration=test_run.configuration,
            created_at=test_run.created_at,
            test_type_name=test_run.test_type.name if test_run.test_type else None,
            environment_name=test_run.environment.name if run.environment else None,
            has_results=test_run.results_cpu_mem is not None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get test run {test_run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test run")


@router.post("/", response_model=TestRunResponse, status_code=201)
async def create_test_run(
    test_run: TestRunCreate,
    db: Session = Depends(get_db_session),
) -> TestRunResponse:
    """Create a new test run."""
    try:
        # Validate test type exists
        test_type = db.query(TestType).filter(TestType.test_type_id == test_run.test_type_id).first()
        if not test_type:
            raise HTTPException(status_code=400, detail="Test type not found")

        # Validate environment exists if provided
        if test_run.environment_id:
            environment = db.query(Environment).filter(Environment.id == test_run.environment_id).first()
            if not environment:
                raise HTTPException(status_code=400, detail="Environment not found")

        # Validate BOMs exist if provided
        if test_run.hw_bom_id:
            hw_bom = db.query(HardwareBOM).filter(HardwareBOM.bom_id == test_run.hw_bom_id).first()
            if not hw_bom:
                raise HTTPException(status_code=400, detail="Hardware BOM not found")

        if test_run.sw_bom_id:
            sw_bom = db.query(SoftwareBOM).filter(SoftwareBOM.bom_id == test_run.sw_bom_id).first()
            if not sw_bom:
                raise HTTPException(status_code=400, detail="Software BOM not found")

        # Create test run
        import uuid
        new_test_run = TestRun(
            test_run_id=str(uuid.uuid4()),
            test_type_id=test_run.test_type_id,
            environment_id=test_run.environment_id,
            hw_bom_id=test_run.hw_bom_id,
            sw_bom_id=test_run.sw_bom_id,
            engineer=test_run.engineer,
            comments=test_run.comments,
            configuration=test_run.configuration or {},
        )

        db.add(new_test_run)
        db.commit()
        db.refresh(new_test_run)

        # Return response
        return TestRunResponse(
            test_run_id=new_test_run.test_run_id,
            test_type_id=new_test_run.test_type_id,
            environment_id=new_test_run.environment_id,
            hw_bom_id=new_test_run.hw_bom_id,
            sw_bom_id=new_test_run.sw_bom_id,
            engineer=new_test_run.engineer,
            comments=new_test_run.comments,
            configuration=new_test_run.configuration,
            created_at=new_test_run.created_at,
            test_type_name=test_type.name,
            environment_name=None,
            has_results=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create test run: {e}")
        raise HTTPException(status_code=500, detail="Failed to create test run")


@router.put("/{test_run_id}", response_model=TestRunResponse)
async def update_test_run(
    test_run_id: str,
    test_run_update: TestRunUpdate,
    db: Session = Depends(get_db_session),
) -> TestRunResponse:
    """Update a test run."""
    try:
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()

        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        # Update fields
        if test_run_update.engineer is not None:
            test_run.engineer = test_run_update.engineer

        if test_run_update.comments is not None:
            test_run.comments = test_run_update.comments

        if test_run_update.configuration is not None:
            test_run.configuration = test_run_update.configuration

        db.commit()
        db.refresh(test_run)

        return TestRunResponse(
            test_run_id=test_run.test_run_id,
            test_type_id=test_run.test_type_id,
            environment_id=test_run.environment_id,
            hw_bom_id=test_run.hw_bom_id,
            sw_bom_id=test_run.sw_bom_id,
            engineer=test_run.engineer,
            comments=test_run.comments,
            configuration=test_run.configuration,
            created_at=test_run.created_at,
            test_type_name=test_run.test_type.name if test_run.test_type else None,
            environment_name=test_run.environment.name if test_run.environment else None,
            has_results=test_run.results_cpu_mem is not None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update test run {test_run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update test run")


@router.delete("/{test_run_id}")
async def delete_test_run(
    test_run_id: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete a test run."""
    try:
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()

        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        db.delete(test_run)
        db.commit()

        return {"message": "Test run deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete test run {test_run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete test run")


@router.get("/stats/overview", response_model=TestRunStats)
async def get_test_run_stats(
    db: Session = Depends(get_db_session),
) -> TestRunStats:
    """Get test run statistics."""
    try:
        # Total runs
        total_runs = db.query(TestRun).count()

        # Runs by type
        runs_by_type = {}
        type_counts = (
            db.query(TestType.name, db.func.count(TestRun.test_run_id))
            .join(TestRun)
            .group_by(TestType.name)
            .all()
        )
        for name, count in type_counts:
            runs_by_type[name] = count

        # Runs by engineer
        runs_by_engineer = {}
        engineer_counts = (
            db.query(TestRun.engineer, db.func.count(TestRun.test_run_id))
            .filter(TestRun.engineer.is_not(None))
            .group_by(TestRun.engineer)
            .all()
        )
        for engineer, count in engineer_counts:
            runs_by_engineer[engineer] = count

        # Recent runs (last 10)
        recent_runs_query = (
            db.query(TestRun)
            .order_by(TestRun.created_at.desc())
            .limit(10)
            .all()
        )

        recent_runs = []
        for run in recent_runs_query:
            recent_runs.append(TestRunResponse(
                test_run_id=run.test_run_id,
                test_type_id=run.test_type_id,
                environment_id=run.environment_id,
                hw_bom_id=run.hw_bom_id,
                sw_bom_id=run.sw_bom_id,
                engineer=run.engineer,
                comments=run.comments,
                configuration=run.configuration,
                created_at=run.created_at,
                test_type_name=run.test_type.name if run.test_type else None,
                environment_name=run.environment.name if run.environment else None,
                has_results=run.results_cpu_mem is not None,
            ))

        return TestRunStats(
            total_runs=total_runs,
            runs_by_type=runs_by_type,
            runs_by_engineer=runs_by_engineer,
            recent_runs=recent_runs,
        )

    except Exception as e:
        logger.error(f"Failed to get test run stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test run statistics")
