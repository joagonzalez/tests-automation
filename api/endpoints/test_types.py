"""Test types API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import TestType
from benchmark_analyzer.core.validator import SchemaValidator, ValidationResult
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class TestTypeBase(BaseModel):
    """Base test type model."""
    name: str = Field(..., min_length=1, max_length=64, description="Test type name")
    description: Optional[str] = Field(None, max_length=500, description="Test type description")


class TestTypeCreate(TestTypeBase):
    """Test type creation model."""
    pass


class TestTypeUpdate(BaseModel):
    """Test type update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=64, description="Test type name")
    description: Optional[str] = Field(None, max_length=500, description="Test type description")


class TestTypeResponse(TestTypeBase):
    """Test type response model."""
    test_type_id: str
    has_schema: bool = False
    test_runs_count: int = 0

    class Config:
        from_attributes = True


class TestTypeListResponse(BaseModel):
    """Test type list response model."""
    items: List[TestTypeResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class TestTypeSchemaResponse(BaseModel):
    """Test type schema response model."""
    test_type_id: str
    name: str
    schema: Dict[str, Any]
    schema_version: Optional[str] = None
    last_updated: Optional[str] = None


class SchemaUploadResponse(BaseModel):
    """Schema upload response model."""
    test_type_id: str
    name: str
    schema_uploaded: bool
    validation_result: Optional[Dict[str, Any]] = None


@router.get("/", response_model=TestTypeListResponse)
async def list_test_types(
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
) -> TestTypeListResponse:
    """List test types with filtering and pagination."""
    try:
        # Build query
        query = db.query(TestType)

        # Apply filters
        if name:
            query = query.filter(TestType.name.ilike(f"%{name}%"))

        # Apply sorting
        if sort_by == "name":
            if sort_order == "desc":
                query = query.order_by(TestType.name.desc())
            else:
                query = query.order_by(TestType.name.asc())

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        test_types = query.offset(offset).limit(page_size).all()

        # Convert to response models
        items = []
        for test_type in test_types:
            # Count test runs for this test type
            test_runs_count = len(test_type.test_runs) if test_type.test_runs else 0

            # Check if schema exists (implement later with schema management)
            has_schema = False  # TODO: Implement schema checking

            item = TestTypeResponse(
                test_type_id=test_type.test_type_id,
                name=test_type.name,
                description=test_type.description,
                has_schema=has_schema,
                test_runs_count=test_runs_count,
            )
            items.append(item)

        return TestTypeListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list test types: {e}")
        raise HTTPException(status_code=500, detail="Failed to list test types")


@router.get("/{test_type_id}", response_model=TestTypeResponse)
async def get_test_type(
    test_type_id: str,
    db: Session = Depends(get_db_session),
) -> TestTypeResponse:
    """Get a specific test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # Count test runs
        test_runs_count = len(test_type.test_runs) if test_type.test_runs else 0

        # Check if schema exists
        has_schema = False  # TODO: Implement schema checking

        return TestTypeResponse(
            test_type_id=test_type.test_type_id,
            name=test_type.name,
            description=test_type.description,
            has_schema=has_schema,
            test_runs_count=test_runs_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get test type {test_type_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test type")


@router.post("/", response_model=TestTypeResponse, status_code=201)
async def create_test_type(
    test_type: TestTypeCreate,
    db: Session = Depends(get_db_session),
) -> TestTypeResponse:
    """Create a new test type."""
    try:
        # Check if test type with same name already exists
        existing = db.query(TestType).filter(TestType.name == test_type.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Test type with name '{test_type.name}' already exists"
            )

        # Create new test type
        import uuid
        new_test_type = TestType(
            test_type_id=str(uuid.uuid4()),
            name=test_type.name,
            description=test_type.description,
        )

        db.add(new_test_type)
        db.commit()
        db.refresh(new_test_type)

        return TestTypeResponse(
            test_type_id=new_test_type.test_type_id,
            name=new_test_type.name,
            description=new_test_type.description,
            has_schema=False,
            test_runs_count=0,
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Database integrity error creating test type: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Test type name must be unique")
    except Exception as e:
        logger.error(f"Failed to create test type: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create test type")


@router.put("/{test_type_id}", response_model=TestTypeResponse)
async def update_test_type(
    test_type_id: str,
    test_type_update: TestTypeUpdate,
    db: Session = Depends(get_db_session),
) -> TestTypeResponse:
    """Update a test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # Check if new name conflicts with existing test type
        if test_type_update.name and test_type_update.name != test_type.name:
            existing = db.query(TestType).filter(TestType.name == test_type_update.name).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Test type with name '{test_type_update.name}' already exists"
                )

        # Update fields
        if test_type_update.name is not None:
            test_type.name = test_type_update.name

        if test_type_update.description is not None:
            test_type.description = test_type_update.description

        db.commit()
        db.refresh(test_type)

        # Count test runs
        test_runs_count = len(test_type.test_runs) if test_type.test_runs else 0

        # Check if schema exists
        has_schema = False  # TODO: Implement schema checking

        return TestTypeResponse(
            test_type_id=test_type.test_type_id,
            name=test_type.name,
            description=test_type.description,
            has_schema=has_schema,
            test_runs_count=test_runs_count,
        )

    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Database integrity error updating test type: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Test type name must be unique")
    except Exception as e:
        logger.error(f"Failed to update test type {test_type_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update test type")


@router.delete("/{test_type_id}")
async def delete_test_type(
    test_type_id: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete a test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # Check if test type has associated test runs
        if test_type.test_runs:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete test type '{test_type.name}' because it has {len(test_type.test_runs)} associated test runs"
            )

        db.delete(test_type)
        db.commit()

        return {"message": f"Test type '{test_type.name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete test type {test_type_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete test type")


@router.get("/{test_type_id}/schema", response_model=TestTypeSchemaResponse)
async def get_test_type_schema(
    test_type_id: str,
    db: Session = Depends(get_db_session),
) -> TestTypeSchemaResponse:
    """Get the schema for a test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # TODO: Implement schema storage and retrieval
        # For now, return a placeholder response
        raise HTTPException(
            status_code=501,
            detail="Schema management not yet implemented"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schema for test type {test_type_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get test type schema")


@router.post("/{test_type_id}/schema", response_model=SchemaUploadResponse)
async def upload_test_type_schema(
    test_type_id: str,
    schema_file: UploadFile = File(..., description="JSON schema file"),
    db: Session = Depends(get_db_session),
) -> SchemaUploadResponse:
    """Upload or update the schema for a test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # Validate file type
        if not schema_file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400,
                detail="Schema file must be a JSON file"
            )

        # Read and parse schema
        import json
        try:
            content = await schema_file.read()
            schema_data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in schema file: {e}"
            )

        # Validate the schema itself
        try:
            from jsonschema import Draft7Validator
            Draft7Validator.check_schema(schema_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON schema: {e}"
            )

        # TODO: Store schema in database or file system
        # For now, return success response
        return SchemaUploadResponse(
            test_type_id=test_type_id,
            name=test_type.name,
            schema_uploaded=True,
            validation_result={
                "valid": True,
                "message": "Schema uploaded successfully (storage not yet implemented)"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload schema for test type {test_type_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload test type schema")


@router.delete("/{test_type_id}/schema")
async def delete_test_type_schema(
    test_type_id: str,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete the schema for a test type."""
    try:
        test_type = db.query(TestType).filter(TestType.test_type_id == test_type_id).first()

        if not test_type:
            raise HTTPException(status_code=404, detail="Test type not found")

        # TODO: Implement schema deletion
        # For now, return placeholder response
        raise HTTPException(
            status_code=501,
            detail="Schema management not yet implemented"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schema for test type {test_type_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete test type schema")
