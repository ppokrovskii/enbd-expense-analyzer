"""FAB (First Abu Dhabi Bank) statement parser."""
from pathlib import Path
import pandas as pd
from .base_parser import BankParser


class FABParser(BankParser):
    """Parser for First Abu Dhabi Bank statements."""
    
    BANK_NAME = "FAB"
    SUPPORTED_FORMATS = ['.xlsx', '.csv', '.xls']
    
    def can_parse(self, file_path: Path) -> tuple[bool, float]:
        """
        Detect if this is a FAB statement.
        
        TODO: Implement detection logic once we have sample files.
        """
        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return (False, 0.0)
        
        try:
            # Read first few rows
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=10)
            else:
                df = pd.read_excel(file_path, nrows=10)
            
            # Look for FAB-specific indicators
            # Check for "FAB", "First Abu Dhabi", etc. in headers or first rows
            text_content = ' '.join(df.astype(str).values.flatten()).upper()
            
            if 'FAB' in text_content or 'FIRST ABU DHABI' in text_content:
                return (True, 0.8)
            
            return (False, 0.0)
            
        except Exception:
            return (False, 0.0)
    
    def parse(self, file_path: Path) -> pd.DataFrame:
        """
        Parse FAB statement.
        
        TODO: Implement parsing logic once we have sample files.
        For now, raise an error to trigger unparsed file storage.
        """
        raise ValueError(
            "FAB parser not yet implemented. "
            "File has been saved for admin review. "
            "A parser will be created based on this file format."
        )

