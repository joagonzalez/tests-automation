"""Environments API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import Environment
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class EnvironmentBase(BaseModel):
    """Base environment model."""
    name: Optional[str] = Field(None, max_length=128, description="Environment name")
    type: Optional[str] = Field(None, max_length=32, description="Environment type")
    comments: Optional[str] = Field(None, max_length=1000, description="Environment comments")
    tools: Optional[Dict[str, Any]] = Field(None, description="Tools configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Environment metadata")


class EnvironmentCreate(EnvironmentBase):
    """Environment creation model."""
    pass


class EnvironmentUpdate(BaseModel):
    """Environment update model."""
    name: Optional[str] = Field(None, max_length=128, description="Environment name")
    type: Optional[str] = Field(None, max_length=32, description="Environment type")
    comments: Optional[str] = Field(None, max_length=1000, description="Environment comments")
    tools: Optional[Dict[str, Any]] = Field(None, description="Tools configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Environment metadata")


class EnvironmentResponse(EnvironmentBase):
    """Environment response model."""
    id: str
    test_runs_count: int = 0

    class Config:
        from_attributes = True


class EnvironmentListResponse(BaseModel):
    """Environment list response model."""
    items: List[EnvironmentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class EnvironmentStats(BaseModel):
    """Environment statistics model."""
    total_environments: int
    environments_by_type: Dict[str, int]
    environments_with_tools: int
    recent_environments: List[EnvironmentResponse]


@router.get("/", response_model=EnvironmentListResponse)
async def list_environments(
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    type: Optional[str] = Query(None, description="Filter by type"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
) -> EnvironmentListResponse:
    """List environments with filtering and pagination."""
    try:
        # Build query
        query = db.query(Environment)

        # Apply filters
        if name:
            query = query.filter(Environment.name.ilike(f"%{name}%"))

        if type:
            query = query.filter(Environment.type == type)

        # Apply sorting
        if sort_by == "name":
            if sort_order == "desc":
                query = query.order_by(Environment.name.desc())
            else:
                query = query.order_by(Environment.name.asc())
        elif sort_by == "type":
            if sort_order == "desc":
                query = query.order_by(Environment.type.desc())
            else:
                query = query.order_by(Environment.type.asc())

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        environments = query.offset(offset).limit(page_size).all()

        # Convert to response models
        items = []
        for env in environments:
            # Count test runs for this environment
            test_runs_count = len(env.test_runs) if env.test_runs else 0

            item = EnvironmentResponse(
                id=env.id,
                name=env.name,
                type=env.type,
                comments=env.comments,
                tools=env.tools,
                metadata=env.env_metadata,
                test_runs_count=test_runs_count,
            )
            items.append(item)

        return EnvironmentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        raise HTTPException(status_code=500, detail="Failed to list environments")


@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str,
    db: Session = Depends(get_db_session),
) -> EnvironmentResponse:
    """Get a specific environment."""
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()

        if not environment:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Count test runs
        test_runs_count = len(environment.test_runs) if environment.test_runs else 0

        return EnvironmentResponse(
            id=environment.id,
            name=environment.name,
            type=environment.type,
            comments=environment.comments,
            tools=environment.tools,
            metadata=environment.env_metadata,
            test_runs_count=test_runs_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get environment {environment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get environment")


@router.post("/", response_model=EnvironmentResponse, status_code=201)
async def create_environment(
    environment: EnvironmentCreate,
    db: Session = Depends(get_db_session),
) -> EnvironmentResponse:
    """Create a new environment."""
    try:
        # Create new environment
        import uuid
        new_environment = Environment(
            id=str(uuid.uuid4()),
            name=environment.name,
            type=environment.type,
            comments=environment.comments,
            tools=environment.tools or {},
            env_metadata=environment.metadata or {},
        )

        db.add(new_environment)
        db.commit()
        db.refresh(new_environment)

        return EnvironmentResponse(
            id=new_environment.id,
            name=new_environment.name,
            type=new_environment.type,
            comments=new_environment.comments,
            tools=new_environment.tools,
            metadata=new_environment.env_metadata,
            test_runs_count=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create environment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create environment")


@router.put("/{environment_id}", response_model=EnvironmentResponse)
async def update_environment(
    environment_id: str,
    environment_update: EnvironmentUpdate,
    db: Session = Depends(get_db_session),
) -> EnvironmentResponse:
    """Update an environment."""
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()

        if not environment:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Update fields
        if environment_update.name is not None:
            environment.name = environment_update.name

        if environment_update.type is not None:
            environment.type = environment_update.type

        if environment_update.comments is not None:
            environment.comments = environment_update.comments

        if environment_update.tools is not None:
            environment.tools = environment_update.tools

        if environment_update.metadata is not None:
            environment.env_metadata = environment_update.metadata

        db.commit()
        db.refresh(environment)

        # Count test runs
        test_runs_count = len(environment.test_runs) if environment.test_runs else 0

        return EnvironmentResponse(
            id=environment.id,
            name=environment.name,
            type=environment.type,
            comments=environment.comments,
            tools=environment.tools,
            metadata=environment.env_metadata,
            test_runs_count=test_runs_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update environment {environment_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update environment")


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete an environment."""
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()

        if not environment:
            raise HTTPException(status_code=404, detail="Environment not found")

        # Check if environment has associated test runs
        if environment.test_runs:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete environment '{environment.name}' because it has {len(environment.test_runs)} associated test runs"
            )

        env_name = environment.name or environment.id
        db.delete(environment)
        db.commit()

        return {"message": f"Environment '{env_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete environment {environment_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete environment")


@router.post("/upload", response_model=EnvironmentResponse)
async def upload_environment_yaml(
    environment_file: UploadFile = File(..., description="YAML environment file"),
    db: Session = Depends(get_db_session),
) -> EnvironmentResponse:
    """Upload an environment from a YAML file."""
    try:
        # Validate file type
        if not environment_file.filename.endswith(('.yaml', '.yml')):
            raise HTTPException(
                status_code=400,
                detail="Environment file must be a YAML file"
            )

        # Read and parse YAML
        import yaml
        try:
            content = await environment_file.read()
            env_data = yaml.safe_load(content.decode('utf-8'))
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid YAML in environment file: {e}"
            )

        # Validate required fields
        if not isinstance(env_data, dict):
            raise HTTPException(
                status_code=400,
                detail="Environment file must contain a YAML object"
            )

        # Create environment from YAML data
        import uuid
        new_environment = Environment(
            id=str(uuid.uuid4()),
            name=env_data.get("name"),
            type=env_data.get("type"),
            comments=env_data.get("comments"),
            tools=env_data.get("tools", {}),
            env_metadata=env_data.get("metadata", {}),
        )

        db.add(new_environment)
        db.commit()
        db.refresh(new_environment)

        return EnvironmentResponse(
            id=new_environment.id,
            name=new_environment.name,
            type=new_environment.type,
            comments=new_environment.comments,
            tools=new_environment.tools,
            metadata=new_environment.env_metadata,
            test_runs_count=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload environment from YAML: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to upload environment")


@router.get("/stats/overview", response_model=EnvironmentStats)
async def get_environment_stats(
    db: Session = Depends(get_db_session),
) -> EnvironmentStats:
    """Get environment statistics."""
    try:
        # Total environments
        total_environments = db.query(Environment).count()

        # Environments by type
        environments_by_type = {}
        type_counts = (
            db.query(Environment.type, db.func.count(Environment.id))
            .filter(Environment.type.is_not(None))
            .group_by(Environment.type)
            .all()
        )
        for env_type, count in type_counts:
            environments_by_type[env_type] = count

        # Environments with tools
        environments_with_tools = (
            db.query(Environment)
            .filter(Environment.tools.is_not(None))
            .filter(Environment.tools != {})
            .count()
        )

        # Recent environments (last 10)
        recent_environments_query = (
            db.query(Environment)
            .order_by(Environment.id.desc())
            .limit(10)
            .all()
        )

        recent_environments = []
        for env in recent_environments_query:
            test_runs_count = len(env.test_runs) if env.test_runs else 0
            recent_environments.append(EnvironmentResponse(
                id=env.id,
                name=env.name,
                type=env.type,
                comments=env.comments,
                tools=env.tools,
                metadata=env.env_metadata,
                test_runs_count=test_runs_count,
            ))

        return EnvironmentStats(
            total_environments=total_environments,
            environments_by_type=environments_by_type,
            environments_with_tools=environments_with_tools,
            recent_environments=recent_environments,
        )

    except Exception as e:
        logger.error(f"Failed to get environment stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get environment statistics")


@router.get("/types/list")
async def list_environment_types(
    db: Session = Depends(get_db_session),
) -> Dict[str, List[str]]:
    """List all available environment types."""
    try:
        types = (
            db.query(Environment.type)
            .filter(Environment.type.is_not(None))
            .distinct()
            .all()
        )

        return {"types": [env_type[0] for env_type in types]}

    except Exception as e:
        logger.error(f"Failed to list environment types: {e}")
        raise HTTPException(status_code=500, detail="Failed to list environment types")
