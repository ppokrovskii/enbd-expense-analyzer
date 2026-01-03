#!/usr/bin/env python3
"""Generate sample ENBD transaction data for additional dummy users."""
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Set random seed for reproducibility
random.seed(42)

# Get project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).parent.parent

# Read the original data
original_file = PROJECT_ROOT / "data/archive/2025-12-26/Current Account Transactions.xlsx"
df_original = pd.read_excel(original_file, header=2)

# Extract actual transactions (skip the header row if it's duplicated in data)
if df_original.iloc[0, 0] == 'Date':
    df_original = df_original.iloc[1:].copy()

# Rename columns properly
df_original.columns = ['Date', 'Details', 'Description', 'Amount', 'Currency', 'Balance', 'Debit/Credit', 'Status']

# Clean amount column
df_original['Amount'] = df_original['Amount'].astype(str).str.replace(',', '').astype(float)

print(f"Loaded {len(df_original)} transactions from original file")


def randomize_amounts(df, variance_factor=0.3):
    """Randomize amounts by +/- variance_factor (e.g., 30%)"""
    df = df.copy()
    df['Amount'] = df['Amount'].apply(
        lambda x: round(x * random.uniform(1 - variance_factor, 1 + variance_factor), 2)
    )
    return df


def recalculate_balance(df, starting_balance=15000.00):
    """Recalculate running balance based on debit/credit"""
    df = df.copy()
    df = df.sort_values('Date', ascending=False)  # Most recent first
    
    balance = starting_balance
    balances = []
    
    for _, row in df.iterrows():
        amount = row['Amount']
        if row['Debit/Credit'] == 'Credit':
            balance += amount
        else:  # Debit
            balance -= amount
        balances.append(round(balance, 2))
    
    df['Balance'] = balances
    return df


def format_amount(amount):
    """Format amount with comma separator"""
    return f"{amount:,.2f}"


def generate_user_data(user_name, account_number, variance_factor=0.3, starting_balance=15000.00):
    """Generate data for one user"""
    print(f"\nGenerating data for {user_name}...")
    
    # Create output directory
    output_dir = PROJECT_ROOT / f"data/archive/{user_name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate Current Account data
    df_user = randomize_amounts(df_original, variance_factor)
    df_user = recalculate_balance(df_user, starting_balance)
    
    # Format amounts and balance with commas for display
    df_display = df_user.copy()
    df_display['Amount'] = df_display['Amount'].apply(format_amount)
    df_display['Balance'] = df_display['Balance'].apply(format_amount)
    
    # Create Excel file with ENBD format (with metadata rows at top)
    output_file = output_dir / "Current Account Transactions.xlsx"
    
    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        workbook = writer.book
        worksheet = workbook.create_sheet('Sheet1')
        
        # Row 1: Account info
        worksheet.cell(1, 1).value = f'Account Number: {account_number}\n         Currency:AED'
        
        # Row 2: Empty
        
        # Row 3: Headers
        headers = ['Date', 'Details', 'Description', 'Amount', 'Currency', 'Balance', 'Debit/Credit', 'Status']
        for col_idx, header in enumerate(headers, 1):
            worksheet.cell(3, col_idx).value = header
        
        # Rows 4+: Data
        for row_idx, (_, row) in enumerate(df_display.iterrows(), 4):
            worksheet.cell(row_idx, 1).value = row['Date']
            worksheet.cell(row_idx, 2).value = row['Details']
            worksheet.cell(row_idx, 3).value = row['Description']
            worksheet.cell(row_idx, 4).value = row['Amount']
            worksheet.cell(row_idx, 5).value = row['Currency']
            worksheet.cell(row_idx, 6).value = row['Balance']
            worksheet.cell(row_idx, 7).value = row['Debit/Credit']
            worksheet.cell(row_idx, 8).value = row['Status']
        
        # Remove default sheet
        if 'Sheet' in workbook.sheetnames:
            del workbook['Sheet']
        
        workbook.save(output_file)
    
    print(f"  ✓ Created: {output_file} ({len(df_user)} transactions)")
    
    return df_user


def generate_account_specific_data(user_name, account_number, base_df, account_type, multiplier=1.0):
    """Generate data for specific account types (Savings, Smart Saver, Millionaire)"""
    output_dir = PROJECT_ROOT / f"data/archive/{user_name}"
    
    # Sample fewer transactions for other accounts
    sample_size = max(5, int(len(base_df) * 0.15))  # ~15% of transactions
    df_account = base_df.sample(n=min(sample_size, len(base_df)), random_state=42)
    
    # Adjust amounts based on account type
    df_account = df_account.copy()
    df_account['Amount'] = df_account['Amount'] * multiplier
    
    # Recalculate balance
    starting_balance = random.uniform(5000, 50000)
    df_account = recalculate_balance(df_account, starting_balance)
    
    # Format for display
    df_display = df_account.copy()
    df_display['Amount'] = df_display['Amount'].apply(format_amount)
    df_display['Balance'] = df_display['Balance'].apply(format_amount)
    
    # Create Excel file
    output_file = output_dir / f"{account_type} Account Transactions.xlsx"
    
    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        workbook = writer.book
        worksheet = workbook.create_sheet('Sheet1')
        
        # Row 1: Account info
        worksheet.cell(1, 1).value = f'Account Number: {account_number}\n         Currency:AED'
        
        # Row 2: Empty
        
        # Row 3: Headers
        headers = ['Date', 'Details', 'Description', 'Amount', 'Currency', 'Balance', 'Debit/Credit', 'Status']
        for col_idx, header in enumerate(headers, 1):
            worksheet.cell(3, col_idx).value = header
        
        # Rows 4+: Data
        for row_idx, (_, row) in enumerate(df_display.iterrows(), 4):
            worksheet.cell(row_idx, 1).value = row['Date']
            worksheet.cell(row_idx, 2).value = row['Details']
            worksheet.cell(row_idx, 3).value = row['Description']
            worksheet.cell(row_idx, 4).value = row['Amount']
            worksheet.cell(row_idx, 5).value = row['Currency']
            worksheet.cell(row_idx, 6).value = row['Balance']
            worksheet.cell(row_idx, 7).value = row['Debit/Credit']
            worksheet.cell(row_idx, 8).value = row['Status']
        
        # Remove default sheet
        if 'Sheet' in workbook.sheetnames:
            del workbook['Sheet']
        
        workbook.save(output_file)
    
    print(f"  ✓ Created: {output_file} ({len(df_account)} transactions)")


if __name__ == "__main__":
    # Generate data for User 2
    print("\n" + "="*60)
    user2_current = generate_user_data(
        user_name="user2_demo",
        account_number="102XXXXXXXX02",
        variance_factor=0.35,
        starting_balance=12500.00
    )

    generate_account_specific_data(
        user_name="user2_demo",
        account_number="102XXXXXXXX03",
        base_df=user2_current,
        account_type="Savings",
        multiplier=2.5
    )

    generate_account_specific_data(
        user_name="user2_demo",
        account_number="102XXXXXXXX04",
        base_df=user2_current,
        account_type="Smart Saver",
        multiplier=5.0
    )

    generate_account_specific_data(
        user_name="user2_demo",
        account_number="102XXXXXXXX05",
        base_df=user2_current,
        account_type="Millionaire",
        multiplier=10.0
    )

    # Generate data for User 3
    print("\n" + "="*60)
    user3_current = generate_user_data(
        user_name="user3_demo",
        account_number="103XXXXXXXX01",
        variance_factor=0.4,
        starting_balance=18000.00
    )

    generate_account_specific_data(
        user_name="user3_demo",
        account_number="103XXXXXXXX02",
        base_df=user3_current,
        account_type="Savings",
        multiplier=3.0
    )

    generate_account_specific_data(
        user_name="user3_demo",
        account_number="103XXXXXXXX03",
        base_df=user3_current,
        account_type="Smart Saver",
        multiplier=7.0
    )

    generate_account_specific_data(
        user_name="user3_demo",
        account_number="103XXXXXXXX04",
        base_df=user3_current,
        account_type="Millionaire",
        multiplier=15.0
    )

    print("\n" + "="*60)
    print("✓ Sample data generation complete!")
    print("\nGenerated directories:")
    print("  - data/archive/user2_demo/")
    print("  - data/archive/user3_demo/")
    print("\nEach directory contains:")
    print("  - Current Account Transactions.xlsx")
    print("  - Savings Account Transactions.xlsx")
    print("  - Smart Saver Account Transactions.xlsx")
    print("  - Millionaire Account Transactions.xlsx")

