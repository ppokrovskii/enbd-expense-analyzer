"""Service for categorizing transactions using rules."""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from .models import Category, Rule
from app.domains.transactions.models import Transaction


class CategoryService:
    """Service for applying category rules to transactions."""
    
    def __init__(self):
        """Initialize the category service."""
        self.rules_cache = None
    
    def load_categories(self, db: Session, user_id: str = 'default_user', person_id: Optional[int] = None) -> Dict[str, Dict]:
        """
        Load all rules from the rules table (not from categories).
        
        Args:
            db: Database session
            user_id: User ID for filtering rules
            person_id: Optional person ID for filtering rules
        
        Returns:
            Dict mapping category names to their config (keywords, exclude_keywords)
        """
        # Query rules with their associated categories
        query = db.query(Rule, Category).join(
            Category, Rule.category_id == Category.id
        ).filter(Rule.user_id == user_id)
        
        if person_id is not None:
            query = query.filter(Rule.person_id == person_id)
        
        rules_query = query.all()
        
        rules_by_category = {}
        for rule, category in rules_query:
            if category.name not in rules_by_category:
                rules_by_category[category.name] = {
                    'keywords': [],
                    'exclude_keywords': []
                }
            
            # Append keywords from this rule
            if rule.keywords:
                rules_by_category[category.name]['keywords'].extend(rule.keywords)
            
            # Append exclude keywords from this rule
            if rule.exclude_keywords:
                rules_by_category[category.name]['exclude_keywords'].extend(rule.exclude_keywords)
        
        return rules_by_category
    
    def categorize_with_variables(
        self, 
        search_text: str, 
        rules: Dict[str, Dict], 
        account_vars: Dict[str, str]
    ) -> str:
        """
        Enhanced categorization with:
        - Account variable substitution
        - Exclude keywords
        - Combined Details+Description matching
        
        Args:
            search_text: Combined text from Details and Description
            rules: Dictionary mapping category names to their config
            account_vars: Account variable substitutions
            
        Returns:
            Category name or "Other"
        """
        if not search_text:
            return "Other"
        
        search_upper = search_text.upper()
        matches = []
        
        for category, config in rules.items():
            # Check exclusions first
            exclude_keywords = config.get('exclude_keywords', [])
            excluded = False
            if exclude_keywords:
                for exclude in exclude_keywords:
                    if exclude and exclude.upper() in search_upper:
                        excluded = True
                        break
            
            if excluded:
                continue  # Skip this category
            
            # Expand account variables in keywords
            keywords = config.get('keywords', [])
            expanded_keywords = []
            for kw in keywords:
                # Replace variables like {current_account}
                expanded_kw = kw
                for var, value in account_vars.items():
                    expanded_kw = expanded_kw.replace(var, value)
                expanded_keywords.append(expanded_kw)
            
            # Match keywords
            for keyword in expanded_keywords:
                if '|' in keyword:
                    # Pipe-separated alternatives
                    alternatives = [alt.strip() for alt in keyword.split('|')]
                    for alt in alternatives:
                        if alt and alt.upper() in search_upper:
                            matches.append((category, len(alt), alt))
                else:
                    keyword_upper = keyword.upper()
                    if keyword_upper in search_upper:
                        matches.append((category, len(keyword), keyword))
        
        # Return longest match (most specific)
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return "Other"
    
    def categorize_merchant(self, merchant: str, rules: Dict[str, Dict], account_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Categorize a single merchant based on rules.
        Prioritizes longer/more-specific keywords over shorter ones.
        """
        if not merchant or merchant == "Unknown":
            return "Other"
        
        merchant_upper = merchant.upper()
        account_vars = account_vars or {}
        
        matches = []
        for category, config in rules.items():
            # Check exclusions
            exclude_keywords = config.get('exclude_keywords', [])
            excluded = False
            for exclude in exclude_keywords:
                if exclude and exclude.upper() in merchant_upper:
                    excluded = True
                    break
            
            if excluded:
                continue
            
            keywords = config.get('keywords', [])
            for keyword in keywords:
                # Expand account variables
                expanded_kw = keyword
                for var, value in account_vars.items():
                    expanded_kw = expanded_kw.replace(var, value)
                
                # Handle keyword_or pattern (pipe-separated alternatives)
                if '|' in expanded_kw:
                    alternatives = [alt.strip() for alt in expanded_kw.split('|')]
                    for alt in alternatives:
                        if alt and alt.upper() in merchant_upper:
                            matches.append((category, len(alt), alt))
                else:
                    keyword_upper = expanded_kw.upper()
                    if keyword_upper in merchant_upper:
                        matches.append((category, len(expanded_kw), expanded_kw))
        
        # Return category with longest matching keyword (most specific)
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]
        
        return "Other"
    
    def categorize_transactions(
        self, 
        db: Session, 
        user_id: str = 'default_user',
        transaction_ids: Optional[List[int]] = None,
        force_recategorize_all: bool = False,
        person_id: Optional[int] = None
    ) -> int:
        """
        Apply category rules to uncategorized transactions (or specified transactions).
        
        Args:
            db: Database session
            user_id: User ID for filtering rules
            transaction_ids: Optional list of specific transaction IDs to categorize
            force_recategorize_all: If True, recategorize ALL transactions, not just "Other"
            person_id: Optional person ID for filtering transactions
        
        Returns:
            Number of transactions categorized
        """
        # Load category rules from rules table
        rules = self.load_categories(db, user_id, person_id=person_id)
        
        # Load account variables
        from app.domains.accounts.service import AccountService
        account_vars = AccountService.get_account_variables(db, user_id)
        
        # Query transactions
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        if person_id is not None:
            query = query.filter(Transaction.person_id == person_id)
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
            # Use search_text for categorization (Details + Description combined)
            new_category = self.categorize_with_variables(
                transaction.search_text or "",
                rules,
                account_vars
            )
            if new_category != transaction.category:
                transaction.category = new_category
                categorized_count += 1
        
        db.commit()
        return categorized_count

