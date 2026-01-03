# Sample Data Generation - Summary

## ✅ Completed

I've successfully generated sample transaction data for 2 additional dummy users for your testing and demos.

## 📁 Generated Data Structure

```
data/archive/
├── 2025-12-26/           # Your original data
│   ├── Current Account Transactions.xlsx
│   ├── Savings Account Transactions.xlsx
│   ├── Smart Saver Account Transactions.xlsx
│   └── Millionaire Account Transactions.xlsx
├── user2_demo/           # Demo User 2
│   ├── Current Account Transactions.xlsx (182 transactions)
│   ├── Savings Account Transactions.xlsx (27 transactions)
│   ├── Smart Saver Account Transactions.xlsx (27 transactions)
│   └── Millionaire Account Transactions.xlsx (27 transactions)
└── user3_demo/           # Demo User 3
    ├── Current Account Transactions.xlsx (182 transactions)
    ├── Savings Account Transactions.xlsx (27 transactions)
    ├── Smart Saver Account Transactions.xlsx (27 transactions)
    └── Millionaire Account Transactions.xlsx (27 transactions)
```

## 🎲 Randomization Details

### User 2 Demo
- **Account Numbers**: 102XXXXXXXX02 (Current), 102XXXXXXXX03 (Savings), 102XXXXXXXX04 (Smart Saver), 102XXXXXXXX05 (Millionaire)
- **Starting Balance**: 12,500 AED (Current Account)
- **Randomization**: ±35% variance on all amounts
- **Balances**: Automatically recalculated to maintain consistency

### User 3 Demo
- **Account Numbers**: 103XXXXXXXX01 (Current), 103XXXXXXXX02 (Savings), 103XXXXXXXX03 (Smart Saver), 103XXXXXXXX04 (Millionaire)
- **Starting Balance**: 18,000 AED (Current Account)
- **Randomization**: ±40% variance on all amounts
- **Balances**: Automatically recalculated to maintain consistency

## ✅ Validation

1. **File Format**: All files follow official ENBD Excel format with metadata rows
2. **Column Structure**: Date, Details, Description, Amount, Currency, Balance, Debit/Credit, Status
3. **Parser Compatible**: Tested with ENBDParser - 100% detection confidence ✓
4. **Running Balances**: All balances properly calculated based on debits/credits
5. **Existing Tests**: All parser tests pass ✓

## 🔧 What Was Done

1. **Created generation script** (`generate_sample_data.py`):
   - Reads your original transaction data
   - Randomizes amounts within specified variance
   - Recalculates running balances
   - Generates 4 account types per user
   - Maintains proper ENBD Excel format

2. **Updated ENBD Parser** (`backend/app/services/parsers/enbd_parser.py`):
   - Enhanced to handle metadata rows (account info at top)
   - Dynamically finds header row
   - Extracts account name from filename when not in data
   - More robust detection logic

3. **Created documentation** (`data/archive/README.md`):
   - Explains data structure
   - Documents randomization approach
   - Usage examples for testing

## 🚀 How to Use

### For Manual Testing
1. Start your backend: `docker-compose up -d`
2. Upload files via API or frontend UI
3. Test with different users by uploading from different folders

### Example API Upload
```bash
# Upload User 2's Current Account
curl -X POST "http://localhost:8000/api/upload" \
  -H "x-user-id: user2_demo" \
  -F "files=@data/archive/user2_demo/Current Account Transactions.xlsx"

# Upload User 3's Savings Account  
curl -X POST "http://localhost:8000/api/upload" \
  -H "x-user-id: user3_demo" \
  -F "files=@data/archive/user3_demo/Savings Account Transactions.xlsx"
```

### For Demos
- **Multi-account scenario**: Upload all 4 files from one user
- **Multi-user testing**: Upload from different user folders
- **Category testing**: Data includes diverse merchants (Carrefour, Talabat, TEMU, etc.)
- **Transfer detection**: Internal transfers between accounts included

## 📊 Transaction Variety

The data includes realistic transaction patterns:
- Salary deposits
- Own account transfers
- P2P transfers (Fastpay)
- Merchants: Groceries, restaurants, shopping, subscriptions
- Services: Taxi, dry cleaning, utilities
- Date range: September 2025 - December 2025

## 🔄 Regenerating Data

To create more users or adjust randomization:
```bash
python3 generate_sample_data.py
```

Edit the script to:
- Change variance factors (0.3 = ±30%)
- Adjust starting balances
- Add more users
- Modify account multipliers

## 📝 Files Modified

1. ✅ `generate_sample_data.py` - New data generation script
2. ✅ `backend/app/services/parsers/enbd_parser.py` - Enhanced parser
3. ✅ `data/archive/README.md` - Documentation
4. ✅ `data/archive/user2_demo/*` - 4 Excel files
5. ✅ `data/archive/user3_demo/*` - 4 Excel files

## ✅ Tests Verified

All existing tests continue to pass:
- ✅ test_enbd_parser_detection
- ✅ test_fab_parser_detection  
- ✅ test_wio_parser_detection
- ✅ test_parser_returns_standard_columns

The generated data is ready for use in your testing and demos! 🎉

