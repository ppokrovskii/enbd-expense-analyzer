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
        Prioritizes longer/more-specific keywords over shorter ones.
        
        Args:
            merchant: Merchant name to categorize
            rules: Dictionary of category names -> keywords
        
        Returns:
            Category name or "Other"
        """
        if not merchant or merchant == "Unknown":
            return "Other"
        
        merchant_upper = merchant.upper()
        
        # Build list of (category, keyword_length, keyword) tuples
        # Sort by keyword length descending (longest/most specific first)
        matches = []
        for category, keywords in rules.items():
            for keyword in keywords:
                # Handle keyword_or pattern (pipe-separated alternatives)
                if '|' in keyword:
                    alternatives = [alt.strip() for alt in keyword.split('|')]
                    for alt in alternatives:
                        if alt and alt.upper() in merchant_upper:
                            matches.append((category, len(alt), alt))
                else:
                    keyword_upper = keyword.upper()
                    if keyword_upper in merchant_upper:
                        matches.append((category, len(keyword), keyword))
        
        # Return category with longest matching keyword (most specific)
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return "Other"
    
    def categorize_transactions(
        self, 
        db: Session, 
        transaction_ids: Optional[List[int]] = None,
        force_recategorize_all: bool = False
    ) -> int:
        """
        Apply category rules to uncategorized transactions (or specified transactions).
        
        Args:
            db: Database session
            transaction_ids: Optional list of specific transaction IDs to categorize
            force_recategorize_all: If True, recategorize ALL transactions, not just "Other"
        
        Returns:
            Number of transactions categorized
        """
        # Load category rules
        rules = self.load_categories(db)
        
        # Query transactions
        query = db.query(Transaction)
        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))
        elif not force_recategorize_all:
            # Match NULL, empty string, or 'Other' (default behavior)
            query = query.filter(
                (Transaction.category.is_(None)) | 
                (Transaction.category == '') | 
                (Transaction.category == 'Other')
            )
        # If force_recategorize_all=True, no filter - process ALL transactions
        
        transactions = query.all()
        
        categorized_count = 0
        for transaction in transactions:
            new_category = self.categorize_merchant(transaction.merchant, rules)
            if new_category != transaction.category:
                transaction.category = new_category
                categorized_count += 1
        
        db.commit()
        return categorized_count
