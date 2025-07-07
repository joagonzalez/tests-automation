"""Results API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import (
    TestRun, TestType, Environment, ResultsCpuMem,
    HardwareBOM, SoftwareBOM
)
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class ResultsBase(BaseModel):
    """Base results model."""
    test_run_id: str
    # Memory metrics
    memory_idle_latency_ns: Optional[float] = None
    memory_peak_injection_bandwidth_mbs: Optional[float] = None
    ramspeed_smp_bandwidth_mbs_add: Optional[float] = None
    ramspeed_smp_bandwidth_mbs_copy: Optional[float] = None
    sysbench_ram_memory_bandwidth_mibs: Optional[int] = None
    sysbench_ram_memory_test_duration_sec: Optional[int] = None
    sysbench_ram_memory_test_mode: Optional[str] = None
    # CPU metrics
    sysbench_cpu_events_per_second: Optional[int] = None
    sysbench_cpu_duration_sec: Optional[int] = None
    sysbench_cpu_test_mode: Optional[str] = None


class ResultsResponse(ResultsBase):
    """Results response model with test run details."""
    # Test run information
    test_type_id: str
    test_type_name: Optional[str] = None
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None
    engineer: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime
    configuration: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ResultsListResponse(BaseModel):
    """Results list response model."""
    items: List[ResultsResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ResultsStats(BaseModel):
    """Results statistics model."""
    total_results: int
    results_by_test_type: Dict[str, int]
    results_by_environment: Dict[str, int]
    date_range: Dict[str, Optional[str]]
    metrics_summary: Dict[str, Dict[str, float]]


class ResultsComparison(BaseModel):
    """Results comparison model."""
    test_run_ids: List[str]
    comparison_metrics: Dict[str, Dict[str, Union[float, int, str]]]
    statistical_analysis: Dict[str, Dict[str, float]]


class MetricDefinition(BaseModel):
    """Metric definition model."""
    name: str
    description: str
    unit: str
    type: str  # 'int', 'float', 'string'
    category: str  # 'memory', 'cpu', 'general'


@router.get("/", response_model=ResultsListResponse)
async def list_results(
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    test_type: Optional[str] = Query(None, description="Filter by test type name"),
    environment: Optional[str] = Query(None, description="Filter by environment name"),
    engineer: Optional[str] = Query(None, description="Filter by engineer"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    metric_min: Optional[float] = Query(None, description="Minimum metric value"),
    metric_max: Optional[float] = Query(None, description="Maximum metric value"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
) -> ResultsListResponse:
    """List test results with filtering and pagination."""
    try:
        # Build query with joins
        query = (
            db.query(ResultsCpuMem, TestRun, TestType, Environment)
            .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
            .join(TestType, TestRun.test_type_id == TestType.test_type_id)
            .outerjoin(Environment, TestRun.environment_id == Environment.id)
        )

        # Apply filters
        if test_type:
            query = query.filter(TestType.name.ilike(f"%{test_type}%"))

        if environment:
            query = query.filter(Environment.name.ilike(f"%{environment}%"))

        if engineer:
            query = query.filter(TestRun.engineer.ilike(f"%{engineer}%"))

        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(TestRun.created_at >= date_from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(TestRun.created_at < date_to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

        # Apply metric filters
        if metric_name and (metric_min is not None or metric_max is not None):
            metric_column = getattr(ResultsCpuMem, metric_name, None)
            if metric_column is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metric name: {metric_name}"
                )

            if metric_min is not None:
                query = query.filter(metric_column >= metric_min)

            if metric_max is not None:
                query = query.filter(metric_column <= metric_max)

        # Apply sorting
        if sort_by == "created_at":
            if sort_order == "desc":
                query = query.order_by(desc(TestRun.created_at))
            else:
                query = query.order_by(asc(TestRun.created_at))
        elif sort_by == "test_type":
            if sort_order == "desc":
                query = query.order_by(desc(TestType.name))
            else:
                query = query.order_by(asc(TestType.name))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()

        # Convert to response models
        items = []
        for result, test_run, test_type, environment in results:
            item = ResultsResponse(
                test_run_id=result.test_run_id,
                # Memory metrics
                memory_idle_latency_ns=result.memory_idle_latency_ns,
                memory_peak_injection_bandwidth_mbs=result.memory_peak_injection_bandwidth_mbs,
                ramspeed_smp_bandwidth_mbs_add=result.ramspeed_smp_bandwidth_mbs_add,
                ramspeed_smp_bandwidth_mbs_copy=result.ramspeed_smp_bandwidth_mbs_copy,
                sysbench_ram_memory_bandwidth_mibs=result.sysbench_ram_memory_bandwidth_mibs,
                sysbench_ram_memory_test_duration_sec=result.sysbench_ram_memory_test_duration_sec,
                sysbench_ram_memory_test_mode=result.sysbench_ram_memory_test_mode,
                # CPU metrics
                sysbench_cpu_events_per_second=result.sysbench_cpu_events_per_second,
                sysbench_cpu_duration_sec=result.sysbench_cpu_duration_sec,
                sysbench_cpu_test_mode=result.sysbench_cpu_test_mode,
                # Test run information
                test_type_id=test_run.test_type_id,
                test_type_name=test_type.name,
                environment_id=test_run.environment_id,
                environment_name=environment.name if environment else None,
                engineer=test_run.engineer,
                comments=test_run.comments,
                created_at=test_run.created_at,
                configuration=test_run.configuration,
            )
            items.append(item)

        return ResultsListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list results: {e}")
        raise HTTPException(status_code=500, detail="Failed to list results")


@router.get("/{test_run_id}", response_model=ResultsResponse)
async def get_result(
    test_run_id: str,
    db: Session = Depends(get_db_session),
) -> ResultsResponse:
    """Get specific test result."""
    try:
        # Query with joins
        result_query = (
            db.query(ResultsCpuMem, TestRun, TestType, Environment)
            .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
            .join(TestType, TestRun.test_type_id == TestType.test_type_id)
            .outerjoin(Environment, TestRun.environment_id == Environment.id)
            .filter(ResultsCpuMem.test_run_id == test_run_id)
            .first()
        )

        if not result_query:
            raise HTTPException(status_code=404, detail="Test result not found")

        result, test_run, test_type, environment = result_query

        return ResultsResponse(
            test_run_id=result.test_run_id,
            # Memory metrics
            memory_idle_latency_ns=result.memory_idle_latency_ns,
            memory_peak_injection_bandwidth_mbs=result.memory_peak_injection_bandwidth_mbs,
            ramspeed_smp_bandwidth_mbs_add=result.ramspeed_smp_bandwidth_mbs_add,
            ramspeed_smp_bandwidth_mbs_copy=result.ramspeed_smp_bandwidth_mbs_copy,
            sysbench_ram_memory_bandwidth_mibs=result.sysbench_ram_memory_bandwidth_mibs,
            sysbench_ram_memory_test_duration_sec=result.sysbench_ram_memory_test_duration_sec,
            sysbench_ram_memory_test_mode=result.sysbench_ram_memory_test_mode,
            # CPU metrics
            sysbench_cpu_events_per_second=result.sysbench_cpu_events_per_second,
            sysbench_cpu_duration_sec=result.sysbench_cpu_duration_sec,
            sysbench_cpu_test_mode=result.sysbench_cpu_test_mode,
            # Test run information
            test_type_id=test_run.test_type_id,
            test_type_name=test_type.name,
            environment_id=test_run.environment_id,
            environment_name=environment.name if environment else None,
            engineer=test_run.engineer,
            comments=test_run.comments,
            created_at=test_run.created_at,
            configuration=test_run.configuration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result {test_run_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get result")


@router.get("/stats/overview", response_model=ResultsStats)
async def get_results_stats(
    db: Session = Depends(get_db_session),
) -> ResultsStats:
    """Get results statistics."""
    try:
        # Total results
        total_results = db.query(ResultsCpuMem).count()

        # Results by test type
        results_by_test_type = {}
        type_counts = (
            db.query(TestType.name, func.count(ResultsCpuMem.test_run_id))
            .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
            .join(TestType, TestRun.test_type_id == TestType.test_type_id)
            .group_by(TestType.name)
            .all()
        )
        for name, count in type_counts:
            results_by_test_type[name] = count

        # Results by environment
        results_by_environment = {}
        env_counts = (
            db.query(Environment.name, func.count(ResultsCpuMem.test_run_id))
            .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
            .join(Environment, TestRun.environment_id == Environment.id)
            .group_by(Environment.name)
            .all()
        )
        for name, count in env_counts:
            results_by_environment[name or "Unknown"] = count

        # Date range
        date_range = {"earliest": None, "latest": None}
        date_stats = (
            db.query(
                func.min(TestRun.created_at),
                func.max(TestRun.created_at)
            )
            .join(ResultsCpuMem, TestRun.test_run_id == ResultsCpuMem.test_run_id)
            .first()
        )
        if date_stats[0]:
            date_range["earliest"] = date_stats[0].isoformat()
        if date_stats[1]:
            date_range["latest"] = date_stats[1].isoformat()

        # Metrics summary
        metrics_summary = {}

        # Memory metrics
        memory_stats = (
            db.query(
                func.avg(ResultsCpuMem.memory_idle_latency_ns),
                func.min(ResultsCpuMem.memory_idle_latency_ns),
                func.max(ResultsCpuMem.memory_idle_latency_ns),
                func.avg(ResultsCpuMem.memory_peak_injection_bandwidth_mbs),
                func.min(ResultsCpuMem.memory_peak_injection_bandwidth_mbs),
                func.max(ResultsCpuMem.memory_peak_injection_bandwidth_mbs),
            )
            .filter(ResultsCpuMem.memory_idle_latency_ns.is_not(None))
            .first()
        )

        if memory_stats[0] is not None:
            metrics_summary["memory_idle_latency_ns"] = {
                "avg": float(memory_stats[0]),
                "min": float(memory_stats[1]),
                "max": float(memory_stats[2]),
            }

        if memory_stats[3] is not None:
            metrics_summary["memory_peak_injection_bandwidth_mbs"] = {
                "avg": float(memory_stats[3]),
                "min": float(memory_stats[4]),
                "max": float(memory_stats[5]),
            }

        # CPU metrics
        cpu_stats = (
            db.query(
                func.avg(ResultsCpuMem.sysbench_cpu_events_per_second),
                func.min(ResultsCpuMem.sysbench_cpu_events_per_second),
                func.max(ResultsCpuMem.sysbench_cpu_events_per_second),
            )
            .filter(ResultsCpuMem.sysbench_cpu_events_per_second.is_not(None))
            .first()
        )

        if cpu_stats[0] is not None:
            metrics_summary["sysbench_cpu_events_per_second"] = {
                "avg": float(cpu_stats[0]),
                "min": float(cpu_stats[1]),
                "max": float(cpu_stats[2]),
            }

        return ResultsStats(
            total_results=total_results,
            results_by_test_type=results_by_test_type,
            results_by_environment=results_by_environment,
            date_range=date_range,
            metrics_summary=metrics_summary,
        )

    except Exception as e:
        logger.error(f"Failed to get results stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get results statistics")


@router.get("/compare/", response_model=ResultsComparison)
async def compare_results(
    test_run_ids: str = Query(..., description="Comma-separated test run IDs"),
    db: Session = Depends(get_db_session),
) -> ResultsComparison:
    """Compare multiple test results."""
    try:
        # Parse test run IDs
        test_run_id_list = [id.strip() for id in test_run_ids.split(",")]

        if len(test_run_id_list) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 test run IDs are required for comparison"
            )

        if len(test_run_id_list) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 test runs can be compared at once"
            )

        # Get results
        results = (
            db.query(ResultsCpuMem, TestRun, TestType)
            .join(TestRun, ResultsCpuMem.test_run_id == TestRun.test_run_id)
            .join(TestType, TestRun.test_type_id == TestType.test_type_id)
            .filter(ResultsCpuMem.test_run_id.in_(test_run_id_list))
            .all()
        )

        if len(results) != len(test_run_id_list):
            found_ids = [r[0].test_run_id for r in results]
            missing_ids = [id for id in test_run_id_list if id not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"Test run IDs not found: {missing_ids}"
            )

        # Build comparison metrics
        comparison_metrics = {}
        metric_names = [
            "memory_idle_latency_ns",
            "memory_peak_injection_bandwidth_mbs",
            "ramspeed_smp_bandwidth_mbs_add",
            "ramspeed_smp_bandwidth_mbs_copy",
            "sysbench_ram_memory_bandwidth_mibs",
            "sysbench_cpu_events_per_second",
            "sysbench_cpu_duration_sec",
        ]

        for metric_name in metric_names:
            comparison_metrics[metric_name] = {}
            for result, test_run, test_type in results:
                value = getattr(result, metric_name)
                comparison_metrics[metric_name][result.test_run_id] = value

        # Statistical analysis
        statistical_analysis = {}
        for metric_name in metric_names:
            values = [
                comparison_metrics[metric_name][test_run_id]
                for test_run_id in test_run_id_list
                if comparison_metrics[metric_name][test_run_id] is not None
            ]

            if values:
                import statistics
                statistical_analysis[metric_name] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "variance": statistics.variance(values) if len(values) > 1 else 0.0,
                }

        return ResultsComparison(
            test_run_ids=test_run_id_list,
            comparison_metrics=comparison_metrics,
            statistical_analysis=statistical_analysis,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare results: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare results")


@router.get("/metrics/definitions", response_model=List[MetricDefinition])
async def get_metric_definitions() -> List[MetricDefinition]:
    """Get available metric definitions."""
    try:
        metrics = [
            MetricDefinition(
                name="memory_idle_latency_ns",
                description="Memory idle latency",
                unit="nanoseconds",
                type="float",
                category="memory"
            ),
            MetricDefinition(
                name="memory_peak_injection_bandwidth_mbs",
                description="Memory peak injection bandwidth",
                unit="MB/s",
                type="float",
                category="memory"
            ),
            MetricDefinition(
                name="ramspeed_smp_bandwidth_mbs_add",
                description="RAMSpeed SMP bandwidth (ADD)",
                unit="MB/s",
                type="float",
                category="memory"
            ),
            MetricDefinition(
                name="ramspeed_smp_bandwidth_mbs_copy",
                description="RAMSpeed SMP bandwidth (COPY)",
                unit="MB/s",
                type="float",
                category="memory"
            ),
            MetricDefinition(
                name="sysbench_ram_memory_bandwidth_mibs",
                description="Sysbench RAM memory bandwidth",
                unit="MiB/s",
                type="int",
                category="memory"
            ),
            MetricDefinition(
                name="sysbench_ram_memory_test_duration_sec",
                description="Sysbench RAM memory test duration",
                unit="seconds",
                type="int",
                category="memory"
            ),
            MetricDefinition(
                name="sysbench_ram_memory_test_mode",
                description="Sysbench RAM memory test mode",
                unit="string",
                type="string",
                category="memory"
            ),
            MetricDefinition(
                name="sysbench_cpu_events_per_second",
                description="Sysbench CPU events per second",
                unit="events/sec",
                type="int",
                category="cpu"
            ),
            MetricDefinition(
                name="sysbench_cpu_duration_sec",
                description="Sysbench CPU test duration",
                unit="seconds",
                type="int",
                category="cpu"
            ),
            MetricDefinition(
                name="sysbench_cpu_test_mode",
                description="Sysbench CPU test mode",
                unit="string",
                type="string",
                category="cpu"
            ),
        ]

        return metrics

    except Exception as e:
        logger.error(f"Failed to get metric definitions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metric definitions")
