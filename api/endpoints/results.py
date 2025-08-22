"""Results API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import (
    TestRun, TestType, Environment, ResultsCpuMem, ResultsNetworkPerf,
    HardwareBOM, SoftwareBOM
)

# Test type to results table mapping
RESULTS_TABLE_MAP = {
    'cpu_mem': ResultsCpuMem,
    'network_perf': ResultsNetworkPerf,
    # Add new test types here:
    # 'io_performance': ResultsIO,
    # 'gpu_compute': ResultsGPU,
}

def get_results_model(test_type_name: str):
    """Get the results model class for a given test type."""
    model = RESULTS_TABLE_MAP.get(test_type_name)
    if not model:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported test type: {test_type_name}. Supported types: {list(RESULTS_TABLE_MAP.keys())}"
        )
    return model
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


class ResultsCreate(BaseModel):
    """Results creation model."""
    results: Dict[str, Any] = Field(..., description="Results data")


@router.post("/{test_run_id}", status_code=status.HTTP_201_CREATED)
async def create_results(
    test_run_id: str,
    results_data: ResultsCreate,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Create results for a test run."""
    try:
        # Check if test run exists and get test type
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()
        if not test_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found"
            )

        # Get the appropriate results model for this test type
        results_model = get_results_model(test_run.test_type.name)

        # Check if results already exist
        existing_results = db.query(results_model).filter(
            results_model.test_run_id == test_run_id
        ).first()
        if existing_results:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Results already exist for this test run"
            )

        # Get valid fields for this results model
        valid_fields = set()
        for column in results_model.__table__.columns:
            if column.name != 'test_run_id':  # Exclude primary key
                valid_fields.add(column.name)

        filtered_results = {
            key: value for key, value in results_data.results.items()
            if key in valid_fields
        }

        logger.info(f"Creating results for test run {test_run_id} with filtered data: {filtered_results}")
        new_results = results_model(
            test_run_id=test_run_id,
            **filtered_results
        )

        db.add(new_results)
        db.commit()

        return {"message": "Results created successfully", "test_run_id": test_run_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create results for test run {test_run_id}: {e}")
        logger.error(f"Results data was: {results_data.results}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create results: {str(e)}"
        )


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
        # For list endpoint, we need to query across all result types
        # Start with test runs and join appropriate results tables
        query = (
            db.query(TestRun, TestType, Environment)
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
        # For metric filtering, we'll need to handle it per test type
        # For now, skip metric filtering in list endpoint to keep it simple
        if metric_name and (metric_min is not None or metric_max is not None):
            logger.warning("Metric filtering not yet supported in list endpoint with dynamic results tables")

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
        # First get the test run to determine the test type
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()
        if not test_run:
            raise HTTPException(status_code=404, detail="Test run not found")

        # Get the appropriate results model and query for results
        results_model = get_results_model(test_run.test_type.name)
        result_data = db.query(results_model).filter(
            results_model.test_run_id == test_run_id
        ).first()

        if not result_data:
            raise HTTPException(status_code=404, detail="Test result not found")

        # Get related data
        test_type = test_run.test_type
        environment = test_run.environment

        return ResultsResponse(
            test_run_id=result_data.test_run_id,
            # Memory metrics
            memory_idle_latency_ns=result_data.memory_idle_latency_ns,
            memory_peak_injection_bandwidth_mbs=result_data.memory_peak_injection_bandwidth_mbs,
            ramspeed_smp_bandwidth_mbs_add=result_data.ramspeed_smp_bandwidth_mbs_add,
            ramspeed_smp_bandwidth_mbs_copy=result_data.ramspeed_smp_bandwidth_mbs_copy,
            sysbench_ram_memory_bandwidth_mibs=result_data.sysbench_ram_memory_bandwidth_mibs,
            sysbench_ram_memory_test_duration_sec=result_data.sysbench_ram_memory_test_duration_sec,
            sysbench_ram_memory_test_mode=result_data.sysbench_ram_memory_test_mode,
            # CPU metrics
            sysbench_cpu_events_per_second=result_data.sysbench_cpu_events_per_second,
            sysbench_cpu_duration_sec=result_data.sysbench_cpu_duration_sec,
            sysbench_cpu_test_mode=result_data.sysbench_cpu_test_mode,
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
        # Count total results across all result types
        total_results = 0
        results_by_test_type = {}

        for test_type_name, results_model in RESULTS_TABLE_MAP.items():
            count = db.query(results_model).count()
            total_results += count
            if count > 0:
                results_by_test_type[test_type_name] = count

        # Results by environment - count test runs that have results
        results_by_environment = {}
        for test_type_name, results_model in RESULTS_TABLE_MAP.items():
            env_counts = (
                db.query(Environment.name, func.count(results_model.test_run_id))
                .join(TestRun, results_model.test_run_id == TestRun.test_run_id)
                .join(Environment, TestRun.environment_id == Environment.id)
                .group_by(Environment.name)
                .all()
            )
            for name, count in env_counts:
                env_name = name or "Unknown"
                results_by_environment[env_name] = results_by_environment.get(env_name, 0) + count

        # Date range - get from test runs that have results
        date_range_query = None
        for test_type_name, results_model in RESULTS_TABLE_MAP.items():
            query_result = (
                db.query(
                    func.min(TestRun.created_at),
                    func.max(TestRun.created_at)
                )
                .join(results_model, TestRun.test_run_id == results_model.test_run_id)
                .first()
            )
            if query_result and query_result[0]:
                if not date_range_query:
                    date_range_query = query_result
                else:
                    # Combine date ranges
                    min_date = min(date_range_query[0], query_result[0])
                    max_date = max(date_range_query[1], query_result[1])
                    date_range_query = (min_date, max_date)
        date_range = {"earliest": None, "latest": None}
        if date_range_query and date_range_query[0]:
            date_range["earliest"] = date_range_query[0].isoformat()
        if date_range_query and date_range_query[1]:
            date_range["latest"] = date_range_query[1].isoformat()

        # Metrics summary
        # Calculate metrics summary - simplified for now
        # TODO: Make this dynamic based on test type
        metrics_summary = {}

        # For now, only calculate metrics for cpu_mem type if it exists
        if 'cpu_mem' in RESULTS_TABLE_MAP and 'cpu_mem' in results_by_test_type:
            results_model = RESULTS_TABLE_MAP['cpu_mem']

            # Memory metrics
            try:
                memory_stats = (
                    db.query(
                        func.avg(results_model.memory_idle_latency_ns),
                        func.min(results_model.memory_idle_latency_ns),
                        func.max(results_model.memory_idle_latency_ns),
                        func.avg(results_model.memory_peak_injection_bandwidth_mbs),
                        func.min(results_model.memory_peak_injection_bandwidth_mbs),
                        func.max(results_model.memory_peak_injection_bandwidth_mbs),
                    )
                    .filter(results_model.memory_idle_latency_ns.is_not(None))
                    .first()
                )

                if memory_stats and memory_stats[0] is not None:
                    metrics_summary["memory_idle_latency_ns"] = {
                        "avg": float(memory_stats[0]),
                        "min": float(memory_stats[1]),
                        "max": float(memory_stats[2])
                    }

                if memory_stats and memory_stats[3] is not None:
                    metrics_summary["memory_peak_injection_bandwidth_mbs"] = {
                        "avg": float(memory_stats[3]),
                        "min": float(memory_stats[4]),
                        "max": float(memory_stats[5])
                    }

                # CPU metrics
                cpu_stats = (
                    db.query(
                        func.avg(results_model.sysbench_cpu_events_per_second),
                        func.min(results_model.sysbench_cpu_events_per_second),
                        func.max(results_model.sysbench_cpu_events_per_second),
                    )
                    .filter(results_model.sysbench_cpu_events_per_second.is_not(None))
                    .first()
                )

                if cpu_stats and cpu_stats[0] is not None:
                    metrics_summary["sysbench_cpu_events_per_second"] = {
                        "avg": float(cpu_stats[0]),
                        "min": float(cpu_stats[1]),
                        "max": float(cpu_stats[2])
                    }
            except Exception as e:
                logger.warning(f"Error calculating metrics summary: {e}")

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
        # Query test runs first, then get results based on test type
        test_runs = (
            db.query(TestRun, TestType)
            .join(TestType, TestRun.test_type_id == TestType.test_type_id)
            .filter(TestRun.test_run_id.in_(test_run_id_list))
            .all()
        )

        if len(test_runs) != len(test_run_id_list):
            raise HTTPException(
                status_code=404,
                detail="One or more test runs not found"
            )

        # Check that all test runs are of the same type
        test_types = {test_type.name for _, test_type in test_runs}
        if len(test_types) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot compare results from different test types: {test_types}"
            )

        test_type_name = list(test_types)[0]
        results_model = get_results_model(test_type_name)

        # Get results for all test runs
        results = []
        for test_run, test_type in test_runs:
            result_data = db.query(results_model).filter(
                results_model.test_run_id == test_run.test_run_id
            ).first()
            if result_data:
                results.append((result_data, test_run, test_type))

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
