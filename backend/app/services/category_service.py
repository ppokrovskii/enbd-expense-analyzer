"""Service for categorizing transactions using rules."""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models import Transaction, Category
import json


class CategoryService:
    """Service for applying category rules to transactions."""
    
    def __init__(self):
        """Initialize the category service."""
        self.rules_cache = None
    
    def load_categories(self, db: Session) -> Dict[str, List[str]]:
        """
        Load all categories and their keywords from the database.
        
        Returns:
            Dict mapping category names to lists of keywords
        """
        if self.rules_cache is not None:
            return self.rules_cache
        
        categories = db.query(Category).all()
        self.rules_cache = {
            cat.name: cat.keywords if cat.keywords else []
            for cat in categories
        }
        return self.rules_cache
    
    def categorize_merchant(self, merchant: str, rules: Dict[str, List[str]]) -> str:
        """
        Categorize a single merchant based on rules.
        
        Args:
            merchant: Merchant name to categorize
            rules: Dictionary of category names -> keywords
        
        Returns:
            Category name or "Other"
        """
        if not merchant or merchant == "Unknown":
            return "Other"
        
        merchant_upper = merchant.upper()
        
        # Check each category's keywords
        for category, keywords in rules.items():
            for keyword in keywords:
                keyword_upper = keyword.upper()
                if keyword_upper in merchant_upper:
                    return category
        
        return "Other"
    
    def categorize_transactions(self, db: Session, transaction_ids: Optional[List[int]] = None) -> int:
        """
        Apply category rules to uncategorized transactions (or specified transactions).
        
        Args:
            db: Database session
            transaction_ids: Optional list of specific transaction IDs to categorize
        
        Returns:
            Number of transactions categorized
        """
        # Load category rules
        rules = self.load_categories(db)
        
        # Query uncategorized transactions (or specific ones)
        query = db.query(Transaction)
        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))
        else:
            # Match NULL, empty string, or 'Other'
            query = query.filter(
                (Transaction.category.is_(None)) | 
                (Transaction.category == '') | 
                (Transaction.category == 'Other')
            )
        
        transactions = query.all()
        
        categorized_count = 0
        for transaction in transactions:
            new_category = self.categorize_merchant(transaction.merchant, rules)
            if new_category != transaction.category:
                transaction.category = new_category
                categorized_count += 1
        
        db.commit()
        return categorized_count
    
    def seed_categories_from_json(self, db: Session, json_path: str) -> int:
        """
        Load categories from a JSON file and insert into database.
        Useful for initializing from the existing categories.json file.
        
        Args:
            db: Database session
            json_path: Path to categories.json file
        
        Returns:
            Number of categories inserted
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        categories_data = data.get('categories', [])
        inserted = 0
        
        for cat_data in categories_data:
            # Check if category already exists
            existing = db.query(Category).filter_by(name=cat_data['name']).first()
            if not existing:
                category = Category(
                    name=cat_data['name'],
                    keywords=cat_data.get('keywords', [])
                )
                db.add(category)
                inserted += 1
        
        db.commit()
        return inserted
