"""BOM (Bill of Materials) endpoints for benchmark analyzer API."""

import logging
from typing import Dict, Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import HardwareBOM, SoftwareBOM, calculate_specs_hash

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class BOMBase(BaseModel):
    """Base BOM model."""
    specs: Dict[str, Any] = Field(..., description="BOM specifications")


class BOMCreate(BOMBase):
    """BOM creation model."""
    pass


class BOMResponse(BOMBase):
    """BOM response model."""
    bom_id: str = Field(..., description="BOM unique identifier")
    specs_hash: str = Field(..., description="Hash of specifications")


class HardwareBOMResponse(BOMResponse):
    """Hardware BOM response model."""
    pass


class SoftwareBOMResponse(BOMResponse):
    """Software BOM response model."""
    kernel_version: Optional[str] = Field(None, description="Kernel version")


# Hardware BOM endpoints
@router.post("/hardware", response_model=HardwareBOMResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_hardware_bom(
    bom: BOMCreate,
    db: Session = Depends(get_db_session),
) -> HardwareBOMResponse:
    """Create or get existing hardware BOM based on specs hash."""
    try:
        # Calculate hash for specs
        specs_hash = calculate_specs_hash(bom.specs)

        # Check if BOM already exists
        existing_bom = db.query(HardwareBOM).filter_by(specs_hash=specs_hash).first()

        if existing_bom:
            logger.info(f"Found existing hardware BOM: {existing_bom.bom_id}")
            return HardwareBOMResponse(
                bom_id=existing_bom.bom_id,
                specs=existing_bom.specs,
                specs_hash=existing_bom.specs_hash
            )

        # Create new BOM
        new_bom = HardwareBOM(
            bom_id=str(uuid.uuid4()),
            specs=bom.specs,
            specs_hash=specs_hash
        )

        db.add(new_bom)
        db.commit()
        db.refresh(new_bom)

        logger.info(f"Created new hardware BOM: {new_bom.bom_id}")

        return HardwareBOMResponse(
            bom_id=new_bom.bom_id,
            specs=new_bom.specs,
            specs_hash=new_bom.specs_hash
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create/get hardware BOM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process hardware BOM: {str(e)}"
        )


@router.get("/hardware/{bom_id}", response_model=HardwareBOMResponse)
async def get_hardware_bom(
    bom_id: str,
    db: Session = Depends(get_db_session),
) -> HardwareBOMResponse:
    """Get hardware BOM by ID."""
    try:
        bom = db.query(HardwareBOM).filter(HardwareBOM.bom_id == bom_id).first()

        if not bom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hardware BOM not found"
            )

        return HardwareBOMResponse(
            bom_id=bom.bom_id,
            specs=bom.specs,
            specs_hash=bom.specs_hash
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hardware BOM {bom_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hardware BOM"
        )


@router.get("/hardware", response_model=List[HardwareBOMResponse])
async def list_hardware_boms(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
) -> List[HardwareBOMResponse]:
    """List hardware BOMs with pagination."""
    try:
        boms = db.query(HardwareBOM).offset(offset).limit(limit).all()

        return [
            HardwareBOMResponse(
                bom_id=bom.bom_id,
                specs=bom.specs,
                specs_hash=bom.specs_hash
            )
            for bom in boms
        ]

    except Exception as e:
        logger.error(f"Failed to list hardware BOMs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve hardware BOMs"
        )


# Software BOM endpoints
@router.post("/software", response_model=SoftwareBOMResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_software_bom(
    bom: BOMCreate,
    db: Session = Depends(get_db_session),
) -> SoftwareBOMResponse:
    """Create or get existing software BOM based on specs hash."""
    try:
        # Calculate hash for specs
        specs_hash = calculate_specs_hash(bom.specs)

        # Check if BOM already exists
        existing_bom = db.query(SoftwareBOM).filter_by(specs_hash=specs_hash).first()

        if existing_bom:
            logger.info(f"Found existing software BOM: {existing_bom.bom_id}")
            return SoftwareBOMResponse(
                bom_id=existing_bom.bom_id,
                specs=existing_bom.specs,
                specs_hash=existing_bom.specs_hash,
                kernel_version=existing_bom.kernel_version
            )

        # Create new BOM
        new_bom = SoftwareBOM(
            bom_id=str(uuid.uuid4()),
            specs=bom.specs,
            specs_hash=specs_hash
        )

        db.add(new_bom)
        db.commit()
        db.refresh(new_bom)

        logger.info(f"Created new software BOM: {new_bom.bom_id}")

        return SoftwareBOMResponse(
            bom_id=new_bom.bom_id,
            specs=new_bom.specs,
            specs_hash=new_bom.specs_hash,
            kernel_version=new_bom.kernel_version
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create/get software BOM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process software BOM: {str(e)}"
        )


@router.get("/software/{bom_id}", response_model=SoftwareBOMResponse)
async def get_software_bom(
    bom_id: str,
    db: Session = Depends(get_db_session),
) -> SoftwareBOMResponse:
    """Get software BOM by ID."""
    try:
        bom = db.query(SoftwareBOM).filter(SoftwareBOM.bom_id == bom_id).first()

        if not bom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Software BOM not found"
            )

        return SoftwareBOMResponse(
            bom_id=bom.bom_id,
            specs=bom.specs,
            specs_hash=bom.specs_hash,
            kernel_version=bom.kernel_version
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get software BOM {bom_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve software BOM"
        )


@router.get("/software", response_model=List[SoftwareBOMResponse])
async def list_software_boms(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
) -> List[SoftwareBOMResponse]:
    """List software BOMs with pagination."""
    try:
        boms = db.query(SoftwareBOM).offset(offset).limit(limit).all()

        return [
            SoftwareBOMResponse(
                bom_id=bom.bom_id,
                specs=bom.specs,
                specs_hash=bom.specs_hash,
                kernel_version=bom.kernel_version
            )
            for bom in boms
        ]

    except Exception as e:
        logger.error(f"Failed to list software BOMs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve software BOMs"
        )
