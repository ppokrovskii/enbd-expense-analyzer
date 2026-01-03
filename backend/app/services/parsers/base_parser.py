"""Base parser interface for bank statement files."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd


class BankParser(ABC):
    """Abstract base class for bank statement parsers."""
    
    BANK_NAME: str = "Unknown"
    SUPPORTED_FORMATS: list = []  # e.g., ['.xlsx', '.csv', '.xls']
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> tuple[bool, float]:
        """
        Detect if this parser can handle the given file.
        
        Returns:
            (can_parse: bool, confidence: float 0-1)
            
        Confidence levels:
        - 1.0: Absolutely certain (found unique identifier)
        - 0.8: Very likely (multiple strong indicators)
        - 0.5: Possible (some indicators match)
        - 0.0: Cannot parse
        """
        pass
    
    @abstractmethod
    def parse(self, file_path: Path) -> pd.DataFrame:
        """
        Parse the file and return standardized DataFrame.
        
        Must return DataFrame with columns:
        - Date: datetime
        - Account: str
        - Description: str
        - Details: str
        - Debit/Credit: str ('DR' or 'CR')
        - Amount: Decimal
        - Balance: Decimal (optional)
        
        Raises:
            ValueError: If file format is invalid
        """
        pass
    
    def get_bank_name(self) -> str:
        """Get the bank name for this parser."""
        return self.BANK_NAME
    
    def detect_format(self, file_path: Path) -> Optional[str]:
        """
        Detect the file format.
        
        Returns:
            Format string ('xlsx', 'csv', 'xls', etc.) or None
        """
        suffix = file_path.suffix.lower()
        return suffix[1:] if suffix else None

