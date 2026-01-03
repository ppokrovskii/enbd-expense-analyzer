"""ENBD (Emirates NBD) bank statement parser."""
from pathlib import Path
from typing import Optional
import pandas as pd
from .base_parser import BankParser


class ENBDParser(BankParser):
    """Parser for Emirates NBD bank statements."""
    
    BANK_NAME = "ENBD"
    SUPPORTED_FORMATS = ['.xlsx', '.xls']
    
    def can_parse(self, file_path: Path) -> tuple[bool, float]:
        """
        Detect if this is an ENBD statement.
        
        Detection strategy:
        1. Check file extension
        2. Try to read Excel file
        3. Look for ENBD-specific column headers
        """
        # Check file extension
        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return (False, 0.0)
        
        try:
            # Try to read the file (first 10 rows to find header)
            df = pd.read_excel(file_path, header=None, nrows=10)
            
            # Find the header row (contains "Date")
            header_row_idx = None
            for idx, row in df.iterrows():
                if row.astype(str).str.contains("Date", case=False, na=False).any():
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                return (False, 0.0)
            
            # Re-read with correct header
            df = pd.read_excel(file_path, header=header_row_idx, nrows=5)
            
            # Look for ENBD-specific columns
            expected_columns = ['Date', 'Description', 'Details', 'Debit/Credit', 'Amount', 'Balance']
            columns_present = sum(1 for col in expected_columns if col in df.columns)
            
            confidence = columns_present / len(expected_columns)
            
            # Additional check: Look for "ENBD" or account number pattern in any cell (first few rows)
            if confidence > 0.5:
                for col in df.columns:
                    cell_values = df[col].astype(str)
                    if cell_values.str.contains('ENBD', case=False, na=False).any():
                        confidence = min(1.0, confidence + 0.2)
                        break
            
            can_parse = confidence >= 0.7
            return (can_parse, confidence)
            
        except Exception as e:
            return (False, 0.0)
    
    def parse(self, file_path: Path) -> pd.DataFrame:
        """
        Parse ENBD Excel statement.
        
        Returns standardized DataFrame with:
        - Date, Account, Description, Details, Debit/Credit, Amount, Balance
        """
        try:
            # Read Excel file without header first
            df = pd.read_excel(file_path, header=None)
            
            # Find the header row (contains "Date")
            header_row_idx = None
            for idx, row in df.iterrows():
                if row.astype(str).str.contains("Date", case=False, na=False).any():
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                raise ValueError(f"Could not find header row in {file_path}")
            
            # Re-read with correct header
            df = pd.read_excel(file_path, header=header_row_idx)
            
            # Drop any rows that are all NaN
            df = df.dropna(how='all')
            
            # Extract account name from filename if Account column doesn't exist
            if 'Account' not in df.columns:
                account_name = file_path.stem.replace(" Transactions", "")
                df['Account'] = account_name
            
            # Validate required columns
            required_cols = ['Date', 'Description', 'Debit/Credit', 'Amount']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Standardize column names and data
            df = df.copy()
            
            # Ensure Date is datetime
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            # Drop rows with invalid dates
            df = df.dropna(subset=['Date'])
            
            # Ensure Amount is numeric
            if df['Amount'].dtype == 'object':
                df['Amount'] = df['Amount'].astype(str).str.replace(',', '').astype(float)
            
            # Handle Balance column (optional)
            if 'Balance' in df.columns:
                if df['Balance'].dtype == 'object':
                    df['Balance'] = df['Balance'].astype(str).str.replace(',', '').replace('', None)
                    df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce')
            
            # Ensure Details column exists
            if 'Details' not in df.columns:
                df['Details'] = ''
            
            # Select and order columns
            output_cols = ['Date', 'Account', 'Description', 'Details', 'Debit/Credit', 'Amount']
            if 'Balance' in df.columns:
                output_cols.append('Balance')
            
            df = df[output_cols]
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to parse ENBD file: {str(e)}")

