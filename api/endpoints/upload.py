"""Upload API endpoints."""

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from benchmark_analyzer.db.connector import get_db_manager
from benchmark_analyzer.db.models import TestRun, TestType, Environment
from benchmark_analyzer.core.loader import DataLoader
from benchmark_analyzer.core.parser import ParserRegistry
from benchmark_analyzer.core.validator import SchemaValidator
from benchmark_analyzer.config import get_config
from api.config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_session():
    """Get database session dependency."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


# Pydantic models
class UploadResponse(BaseModel):
    """Upload response model."""
    upload_id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    message: str
    uploaded_at: str


class ProcessingResult(BaseModel):
    """Processing result model."""
    upload_id: str
    status: str
    message: str
    test_run_id: Optional[str] = None
    processed_files: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []


class ImportRequest(BaseModel):
    """Import request model."""
    test_type: str = Field(..., description="Test type name")
    environment_id: Optional[str] = Field(None, description="Environment ID")
    engineer: Optional[str] = Field(None, description="Engineer name")
    comments: Optional[str] = Field(None, description="Comments")
    auto_create_test_type: bool = Field(True, description="Auto-create test type if not exists")


class BulkUploadResponse(BaseModel):
    """Bulk upload response model."""
    upload_ids: List[str]
    successful_uploads: int
    failed_uploads: int
    total_size: int
    errors: List[str] = []


class FileInfo(BaseModel):
    """File information model."""
    upload_id: str
    filename: str
    file_size: int
    file_type: str
    uploaded_at: str
    status: str
    processing_result: Optional[ProcessingResult] = None


def get_upload_dir() -> Path:
    """Get upload directory."""
    upload_dir = Path(config.get("upload", {}).get("directory", "/tmp/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_temp_dir() -> Path:
    """Get temporary directory."""
    temp_dir = Path(config.get("upload", {}).get("temp_directory", "/tmp/temp"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def validate_file_size(file_size: int) -> None:
    """Validate file size."""
    max_size = config.get("upload", {}).get("max_file_size", 100 * 1024 * 1024)  # 100MB default
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size {file_size} bytes exceeds maximum allowed size of {max_size} bytes"
        )


def validate_file_type(filename: str, allowed_types: List[str]) -> None:
    """Validate file type."""
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Allowed types: {allowed_types}"
        )


def save_uploaded_file(file: UploadFile, upload_id: str) -> Path:
    """Save uploaded file to disk."""
    upload_dir = get_upload_dir()
    file_path = upload_dir / f"{upload_id}_{file.filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_path
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    file_type: str = Form(..., description="File type: 'test_results', 'environment', 'schema', 'bom'"),
) -> UploadResponse:
    """Upload a single file."""
    try:
        # Generate upload ID
        upload_id = str(uuid4())

        # Validate file size
        if file.size:
            validate_file_size(file.size)

        # Validate file type based on purpose
        if file_type == "test_results":
            validate_file_type(file.filename, [".zip"])
        elif file_type == "environment":
            validate_file_type(file.filename, [".yaml", ".yml"])
        elif file_type == "schema":
            validate_file_type(file.filename, [".json"])
        elif file_type == "bom":
            validate_file_type(file.filename, [".yaml", ".yml"])
        else:
            raise HTTPException(status_code=400, detail="Invalid file_type")

        # Save file
        file_path = save_uploaded_file(file, upload_id)

        # Create response
        from datetime import datetime
        response = UploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file.size or 0,
            file_type=file_type,
            status="uploaded",
            message="File uploaded successfully",
            uploaded_at=datetime.utcnow().isoformat(),
        )

        logger.info(f"File uploaded: {file.filename} -> {upload_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.post("/bulk", response_model=BulkUploadResponse)
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="Files to upload"),
    file_type: str = Form(..., description="File type for all files"),
) -> BulkUploadResponse:
    """Upload multiple files."""
    try:
        upload_ids = []
        errors = []
        total_size = 0
        successful_uploads = 0
        failed_uploads = 0

        for file in files:
            try:
                # Generate upload ID
                upload_id = str(uuid4())

                # Validate and save file
                if file.size:
                    validate_file_size(file.size)
                    total_size += file.size

                # Validate file type
                if file_type == "test_results":
                    validate_file_type(file.filename, [".zip"])
                elif file_type in ["environment", "bom"]:
                    validate_file_type(file.filename, [".yaml", ".yml"])
                elif file_type == "schema":
                    validate_file_type(file.filename, [".json"])

                # Save file
                save_uploaded_file(file, upload_id)

                upload_ids.append(upload_id)
                successful_uploads += 1

                logger.info(f"File uploaded in bulk: {file.filename} -> {upload_id}")

            except Exception as e:
                failed_uploads += 1
                error_msg = f"Failed to upload {file.filename}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        return BulkUploadResponse(
            upload_ids=upload_ids,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            total_size=total_size,
            errors=errors,
        )

    except Exception as e:
        logger.error(f"Failed to upload multiple files: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload multiple files")


@router.post("/{upload_id}/process", response_model=ProcessingResult)
async def process_uploaded_file(
    upload_id: str,
    import_request: ImportRequest,
    db: Session = Depends(get_db_session),
) -> ProcessingResult:
    """Process an uploaded test results file."""
    try:
        # Find uploaded file
        upload_dir = get_upload_dir()
        uploaded_files = list(upload_dir.glob(f"{upload_id}_*"))

        if not uploaded_files:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_path = uploaded_files[0]

        # Validate file is a zip file for test results
        if not file_path.name.endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail="Only zip files can be processed as test results"
            )

        # Initialize processing result
        result = ProcessingResult(
            upload_id=upload_id,
            status="processing",
            message="Processing started",
        )

        # Create temporary directory for extraction
        temp_dir = get_temp_dir()
        extract_dir = temp_dir / f"extract_{upload_id}"
        extract_dir.mkdir(exist_ok=True)

        try:
            # Extract zip file
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Get extracted files
            extracted_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            result.processed_files = [str(Path(f).name) for f in extracted_files]

            # Get or create test type
            test_type = db.query(TestType).filter(TestType.name == import_request.test_type).first()

            if not test_type:
                if import_request.auto_create_test_type:
                    # Create new test type
                    test_type = TestType(
                        test_type_id=str(uuid4()),
                        name=import_request.test_type,
                        description=f"Auto-created test type for {import_request.test_type}",
                    )
                    db.add(test_type)
                    db.commit()
                    db.refresh(test_type)
                    result.warnings.append(f"Created new test type: {import_request.test_type}")
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Test type '{import_request.test_type}' not found"
                    )

            # Validate environment if provided
            environment = None
            if import_request.environment_id:
                environment = db.query(Environment).filter(Environment.id == import_request.environment_id).first()
                if not environment:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Environment '{import_request.environment_id}' not found"
                    )

            # Create test run
            test_run = TestRun(
                test_run_id=str(uuid4()),
                test_type_id=test_type.test_type_id,
                environment_id=import_request.environment_id,
                engineer=import_request.engineer,
                comments=import_request.comments,
                configuration={"upload_id": upload_id, "processed_files": result.processed_files},
            )

            db.add(test_run)
            db.commit()
            db.refresh(test_run)

            # TODO: Process individual files using parsers
            # This would involve:
            # 1. Identifying file types
            # 2. Using appropriate parsers
            # 3. Validating against schemas
            # 4. Inserting results into database

            result.status = "completed"
            result.message = "File processed successfully"
            result.test_run_id = test_run.test_run_id

            logger.info(f"File processed successfully: {upload_id} -> {test_run.test_run_id}")

        except Exception as e:
            result.status = "failed"
            result.message = f"Processing failed: {str(e)}"
            result.errors.append(str(e))
            logger.error(f"File processing failed: {upload_id} -> {e}")

        finally:
            # Clean up temporary directory
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")


@router.get("/{upload_id}/info", response_model=FileInfo)
async def get_file_info(upload_id: str) -> FileInfo:
    """Get information about an uploaded file."""
    try:
        upload_dir = get_upload_dir()
        uploaded_files = list(upload_dir.glob(f"{upload_id}_*"))

        if not uploaded_files:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_path = uploaded_files[0]
        file_stat = file_path.stat()

        # Extract original filename
        original_filename = file_path.name[len(upload_id) + 1:]  # Remove upload_id prefix

        # Determine file type
        file_ext = file_path.suffix.lower()
        if file_ext == '.zip':
            file_type = 'test_results'
        elif file_ext in ['.yaml', '.yml']:
            file_type = 'environment_or_bom'
        elif file_ext == '.json':
            file_type = 'schema'
        else:
            file_type = 'unknown'

        return FileInfo(
            upload_id=upload_id,
            filename=original_filename,
            file_size=file_stat.st_size,
            file_type=file_type,
            uploaded_at=datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            status="uploaded",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file info")


@router.delete("/{upload_id}")
async def delete_uploaded_file(upload_id: str) -> Dict[str, str]:
    """Delete an uploaded file."""
    try:
        upload_dir = get_upload_dir()
        uploaded_files = list(upload_dir.glob(f"{upload_id}_*"))

        if not uploaded_files:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_path = uploaded_files[0]
        original_filename = file_path.name[len(upload_id) + 1:]

        # Delete file
        file_path.unlink()

        logger.info(f"Deleted uploaded file: {upload_id} ({original_filename})")

        return {"message": f"File '{original_filename}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete uploaded file")


@router.get("/", response_model=List[FileInfo])
async def list_uploaded_files(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of files to return"),
    offset: int = Query(0, ge=0, description="Number of files to skip"),
) -> List[FileInfo]:
    """List uploaded files."""
    try:
        upload_dir = get_upload_dir()

        # Get all uploaded files
        all_files = list(upload_dir.glob("*"))
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Apply pagination
        files = all_files[offset:offset + limit]

        file_infos = []
        for file_path in files:
            try:
                # Extract upload ID from filename
                filename_parts = file_path.name.split('_', 1)
                if len(filename_parts) != 2:
                    continue  # Skip files that don't match pattern

                upload_id = filename_parts[0]
                original_filename = filename_parts[1]

                file_stat = file_path.stat()

                # Determine file type
                file_ext = file_path.suffix.lower()
                if file_ext == '.zip':
                    file_type = 'test_results'
                elif file_ext in ['.yaml', '.yml']:
                    file_type = 'environment_or_bom'
                elif file_ext == '.json':
                    file_type = 'schema'
                else:
                    file_type = 'unknown'

                file_info = FileInfo(
                    upload_id=upload_id,
                    filename=original_filename,
                    file_size=file_stat.st_size,
                    file_type=file_type,
                    uploaded_at=datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    status="uploaded",
                )
                file_infos.append(file_info)

            except Exception as e:
                logger.warning(f"Failed to process file {file_path}: {e}")
                continue

        return file_infos

    except Exception as e:
        logger.error(f"Failed to list uploaded files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list uploaded files")


@router.post("/cleanup")
async def cleanup_old_files(
    days_old: int = Query(7, ge=1, le=365, description="Delete files older than N days"),
) -> Dict[str, Any]:
    """Clean up old uploaded files."""
    try:
        from datetime import datetime, timedelta

        upload_dir = get_upload_dir()
        cutoff_time = datetime.now() - timedelta(days=days_old)

        deleted_files = []
        total_size_freed = 0

        for file_path in upload_dir.glob("*"):
            try:
                file_stat = file_path.stat()
                file_time = datetime.fromtimestamp(file_stat.st_mtime)

                if file_time < cutoff_time:
                    file_size = file_stat.st_size
                    total_size_freed += file_size
                    deleted_files.append({
                        "filename": file_path.name,
                        "size": file_size,
                        "uploaded_at": file_time.isoformat(),
                    })
                    file_path.unlink()

            except Exception as e:
                logger.warning(f"Failed to process file {file_path} during cleanup: {e}")
                continue

        logger.info(f"Cleanup completed: {len(deleted_files)} files deleted, {total_size_freed} bytes freed")

        return {
            "deleted_files": len(deleted_files),
            "total_size_freed": total_size_freed,
            "files": deleted_files,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old files: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup old files")
