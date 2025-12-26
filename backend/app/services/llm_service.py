"""Service for LLM-powered categorization using OpenAI."""
import os
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models import Transaction, LLMCache, Category

load_dotenv()


class LLMCategorizationService:
    """Service for categorizing transactions using LLM with caching."""
    
    SYSTEM_PROMPT = """You are an expense categorization assistant. Your job is to categorize merchant names into one of the following categories:

**Primary Categories:**
- Food & Dining (restaurants, cafes, fast food, food delivery)
- Groceries (supermarkets, grocery stores, fresh markets)
- Shopping (retail stores, clothing, electronics, online shopping)
- Transportation (ride-hailing, taxi, public transport, parking)
- Telecommunications (mobile operators, internet providers, phone bills)
- Entertainment (cinemas, concerts, streaming services like Netflix/Prime)
- Technology Subscriptions (software subscriptions, cloud services, development tools)
- Health & Fitness (gyms, medical services, pharmacies, wellness)
- Travel & Tourism (hotels, flights, tourism activities)
- Utilities (electricity, water, cooling services like Empower/Emicool)
- Salary (income from employer)
- Transfer Between My Accounts (internal transfers between own accounts)
- Incoming Transfer (money received from others)
- Outgoing Transfer (money sent to others)
- Other (anything that doesn't fit above)

**Important Rules for Transfers:**
- If merchant contains "TRANSFER TO" or "TRANSFER FROM" with account numbers → "Transfer Between My Accounts"
- If merchant is a person's name (e.g., "John Doe", "Maria Smith") → likely "Outgoing Transfer"
- If merchant is "SALARY", "PAYROLL", or employer name → "Salary"
- Generic incoming payments → "Incoming Transfer"

**Examples:**
- "CARREFOUR HYPERMARKET" → Groceries
- "UBER TRIP" → Transportation
- "AIRALO" → Telecommunications
- "LRIL ONLINE" → Shopping
- "KARTINA.TV" → Entertainment
- "SUNO.AI" or "TUNECORE" → Technology Subscriptions
- "PAUL BAKERY" → Food & Dining
- "MICROSOFT 365" or "CURSOR.COM" → Technology Subscriptions
- "DU TELECOM" → Telecommunications
- "DUBAI ELECTRICITY" → Utilities
- "TRANSFER TO ACCOUNT 1234567890" → Transfer Between My Accounts

Return ONLY the category name, nothing else."""

    USER_PROMPT_TEMPLATE = "Categorize this merchant: {merchant}"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to OPENAI_MODEL env var or gpt-5.2)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        # Lazy import to avoid dependency when not using LLM
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
    
    def categorize_with_llm(self, merchant: str) -> str:
        """
        Categorize a single merchant using LLM.
        
        Args:
            merchant: Merchant name
        
        Returns:
            Category name
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": self.USER_PROMPT_TEMPLATE.format(merchant=merchant)}
                ],
                temperature=0.0,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            return category if category else "Other"
        
        except Exception as e:
            print(f"Error calling LLM for merchant '{merchant}': {e}")
            return "Other"
    
    def get_cached_category(self, merchant: str, db: Session) -> Optional[str]:
        """
        Get category from cache if it exists.
        
        Args:
            merchant: Merchant name
            db: Database session
        
        Returns:
            Category name if cached, None otherwise
        """
        cache_entry = db.query(LLMCache).filter_by(merchant=merchant).first()
        return cache_entry.category if cache_entry else None
    
    def cache_category(self, merchant: str, category: str, db: Session):
        """
        Cache a merchant's category.
        
        Args:
            merchant: Merchant name
            category: Category name
            db: Database session
        """
        # Check if already exists
        existing = db.query(LLMCache).filter_by(merchant=merchant).first()
        if existing:
            existing.category = category
        else:
            cache_entry = LLMCache(merchant=merchant, category=category)
            db.add(cache_entry)
        db.commit()
    
    def categorize_uncategorized_transactions(self, db: Session, limit: Optional[int] = None) -> dict:
        """
        Categorize all "Other" transactions using LLM with caching.
        
        Args:
            db: Database session
            limit: Optional limit on number of transactions to process
        
        Returns:
            Dictionary with statistics: {
                'processed': int,
                'cached': int,
                'llm_calls': int,
                'categorized': int
            }
        """
        # Get all "Other" transactions
        query = db.query(Transaction).filter(Transaction.category == 'Other')
        if limit:
            query = query.limit(limit)
        
        transactions = query.all()
        
        stats = {
            'processed': 0,
            'cached': 0,
            'llm_calls': 0,
            'categorized': 0
        }
        
        # Group by merchant to avoid redundant calls
        merchant_to_transactions = {}
        for trans in transactions:
            if trans.merchant not in merchant_to_transactions:
                merchant_to_transactions[trans.merchant] = []
            merchant_to_transactions[trans.merchant].append(trans)
        
        # Process each unique merchant
        for merchant, trans_list in merchant_to_transactions.items():
            stats['processed'] += len(trans_list)
            
            # Check cache first
            cached_category = self.get_cached_category(merchant, db)
            
            if cached_category:
                category = cached_category
                stats['cached'] += len(trans_list)
            else:
                # Call LLM
                category = self.categorize_with_llm(merchant)
                self.cache_category(merchant, category, db)
                stats['llm_calls'] += 1
            
            # Update all transactions with this merchant
            for trans in trans_list:
                if trans.category != category:
                    trans.category = category
                    stats['categorized'] += 1
        
        db.commit()
        return stats

