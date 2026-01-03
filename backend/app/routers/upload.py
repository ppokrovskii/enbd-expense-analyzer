"""Upload API endpoints with multi-bank support."""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel
import tempfile
import shutil

from app.database import get_db
from app.dependencies import get_user_id
from app.services.multi_bank_import_service import MultiBankImportService

router = APIRouter(prefix="/api", tags=["upload"])


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool
    files_processed: int
    transactions_added: int
    duplicates_skipped: int
    detected_banks: dict  # filename -> bank name
    unparsed_files: List[dict]  # Files that couldn't be parsed


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    bank_name: Optional[str] = None,  # User can specify bank name
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Upload bank statement files with automatic format detection.
    
    Supports:
    - Automatic bank detection
    - Multiple file formats (.xlsx, .xls, .csv)
    - Multiple banks (ENBD, FAB, WIO, etc.)
    - Fallback to unparsed files storage for unknown formats
    
    Args:
        files: List of uploaded files
        bank_name: Optional bank name hint
        db: Database session
        user_id: User ID
        
    Returns:
        Import statistics including detected banks and unparsed files
    """
    # Validate files have allowed extensions
    allowed_extensions = ['.xlsx', '.xls', '.csv']
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Allowed: {', '.join(allowed_extensions)}"
            )
    
    # Save uploaded files to temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    temp_files = []
    
    try:
        for file in files:
            temp_file_path = temp_dir / file.filename
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_files.append(temp_file_path)
        
        # Import files
        total_added = 0
        total_skipped = 0
        detected_banks = {}
        unparsed_files = []
        
        for file_path in temp_files:
            result = MultiBankImportService.import_file(file_path, db, user_id, bank_name)
            
            if result['success']:
                total_added += result['transactions_added']
                total_skipped += result['duplicates_skipped']
                detected_banks[file_path.name] = {
                    'bank': result['detected_bank'],
                    'confidence': result['detection_confidence']
                }
            else:
                # File couldn't be parsed
                unparsed_files.append({
                    'filename': file_path.name,
                    'error': result['error'],
                    'unparsed_file_id': result.get('unparsed_file_id'),
                    'detected_bank': result.get('detected_bank'),
                    'requires_bank_name': result.get('requires_bank_name', False)
                })
        
        return UploadResponse(
            success=len(unparsed_files) == 0,  # Success if all files parsed
            files_processed=len(temp_files),
            transactions_added=total_added,
            duplicates_skipped=total_skipped,
            detected_banks=detected_banks,
            unparsed_files=unparsed_files
        )
    
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Upload error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)

