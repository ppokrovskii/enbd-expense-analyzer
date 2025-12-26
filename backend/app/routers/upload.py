"""Upload API endpoints."""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import tempfile
import shutil

from app.database import get_db
from app.services.import_service import ImportService

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_xlsx(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload ENBD XLSX files and import transactions.
    
    Returns:
        Statistics about the import process
    """
    # Validate files
    for file in files:
        if not file.filename.endswith('.xlsx'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only .xlsx files are allowed."
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
        import_service = ImportService()
        stats = import_service.import_multiple_files(temp_files, db)
        
        return {
            "success": True,
            "files_processed": stats['files_processed'],
            "transactions_added": stats['transactions_added'],
            "duplicates_skipped": stats['duplicates_skipped']
        }
    
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Upload error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup temporary files
        shutil.rmtree(temp_dir, ignore_errors=True)

