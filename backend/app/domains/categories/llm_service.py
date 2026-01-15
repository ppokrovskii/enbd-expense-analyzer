"""Service for LLM-powered categorization using OpenAI."""
import os
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .models import LLMCache, Category
from app.domains.transactions.models import Transaction
from app.shared.exceptions import (
    LLMError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    parse_openai_error
)

load_dotenv()


class LLMCategorizationService:
    """Service for categorizing transactions using LLM with caching."""
    
    # Default categories for new users
    DEFAULT_CATEGORIES = [
        "Food & Dining",
        "Groceries",
        "Shopping",
        "Transport",
        "Telecommunications",
        "Entertainment",
        "Technology Subscriptions",
        "Healthcare",
        "Travel & Tourism",
        "Utilities",
        "Salary",
        "Incoming Transfer",
        "Outgoing Transfer",
        "Other"
    ]
    
    # Standard MCC-based categories that neobanks commonly use
    STANDARD_MCC_CATEGORIES = [
        "Automotive & Gas Stations",
        "Books & Magazines",
        "Business Services",
        "Cafes & Coffee Shops",
        "Charity & Donations",
        "Childcare & Education",
        "Clothing & Apparel",
        "Electronics & Appliances",
        "Fast Food & Quick Service",
        "Fitness & Gym",
        "Food & Dining",
        "Government Services",
        "Groceries",
        "Healthcare",
        "Home Improvement & Furniture",
        "Hotels & Accommodation",
        "Insurance",
        "Internet & Cable",
        "Jewelry & Accessories",
        "Legal & Professional Services",
        "Movies & Cinema",
        "Online Services & Software",
        "Parking & Tolls",
        "Personal Care & Beauty",
        "Pet Care",
        "Pharmacies & Medical",
        "Public Transport",
        "Rent & Mortgage",
        "Restaurants & Bars",
        "Rideshare & Taxis",
        "Shopping",
        "Sports & Recreation",
        "Streaming & Subscriptions",
        "Supermarkets",
        "Technology Subscriptions",
        "Telecommunications",
        "Travel & Tourism",
        "Utilities",
        "Other"
    ]
    
    USER_PROMPT_TEMPLATE = "Categorize this merchant: {merchant}"
    
    def __init__(self, db: Session, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize LLM service."""
        self.db = db
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.system_prompt = self._build_system_prompt()
        
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt dynamically from database categories."""
        categories = self.db.query(Category).all()
        category_names = [c.name for c in categories] if categories else self.DEFAULT_CATEGORIES
        
        if "Other" not in category_names:
            category_names.append("Other")
        
        category_list = "\n".join([f"- {cat}" for cat in sorted(category_names)])
        standard_categories_list = "\n".join([f"- {cat}" for cat in sorted(self.STANDARD_MCC_CATEGORIES)])
        
        return f"""You are an expense categorization assistant. Categorize merchant/transaction descriptions.

**USER'S CATEGORIES:**
{category_list}

**STANDARD MCC CATEGORIES (for suggestions):**
{standard_categories_list}

**TRANSFER RULES:**
- "TRANSFER FROM" = Incoming Transfer
- "TRANSFER TO" = Outgoing Transfer
- Salary/payroll = Salary

Return ONLY the category name."""
    
    def categorize_with_llm(self, merchant: str, raise_on_error: bool = False) -> str:
        """Categorize a single merchant using LLM.
        
        Args:
            merchant: The merchant name to categorize
            raise_on_error: If True, raises LLMError on failure instead of returning "Other"
        
        Returns:
            Category name string
            
        Raises:
            LLMError: If raise_on_error is True and an error occurs
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.USER_PROMPT_TEMPLATE.format(merchant=merchant)}
                ],
                temperature=0.0,
                max_tokens=50
            )
            category = response.choices[0].message.content.strip()
            return category if category else "Other"
        except Exception as e:
            print(f"Error calling LLM for merchant '{merchant}': {e}")
            if raise_on_error:
                raise parse_openai_error(e) from e
            return "Other"
    
    def get_cached_category(self, merchant: str, db: Session) -> Optional[str]:
        """Get category from cache if it exists."""
        cache_entry = db.query(LLMCache).filter_by(merchant=merchant).first()
        return cache_entry.category if cache_entry else None
    
    def cache_category(self, merchant: str, category: str, db: Session):
        """Cache a merchant's category."""
        existing = db.query(LLMCache).filter_by(merchant=merchant).first()
        if existing:
            existing.category = category
        else:
            cache_entry = LLMCache(merchant=merchant, category=category)
            db.add(cache_entry)
        db.commit()
    
    def categorize_uncategorized_transactions(self, db: Session, limit: Optional[int] = None) -> dict:
        """Categorize all 'Other' transactions using LLM with caching."""
        query = db.query(Transaction).filter(Transaction.category == 'Other')
        if limit:
            query = query.limit(limit)
        
        transactions = query.all()
        stats = {'processed': 0, 'cached': 0, 'llm_calls': 0, 'categorized': 0}
        
        merchant_to_transactions = {}
        for trans in transactions:
            if trans.merchant not in merchant_to_transactions:
                merchant_to_transactions[trans.merchant] = []
            merchant_to_transactions[trans.merchant].append(trans)
        
        for merchant, trans_list in merchant_to_transactions.items():
            stats['processed'] += len(trans_list)
            cached_category = self.get_cached_category(merchant, db)
            
            if cached_category:
                category = cached_category
                stats['cached'] += len(trans_list)
            else:
                category = self.categorize_with_llm(merchant)
                self.cache_category(merchant, category, db)
                stats['llm_calls'] += 1
            
            for trans in trans_list:
                if trans.category != category:
                    trans.category = category
                    stats['categorized'] += 1
        
        db.commit()
        return stats

    def bulk_suggest_categories(self, merchants: List[str], raise_on_error: bool = True) -> List[dict]:
        """Get AI suggestions for multiple merchants using function calling.
        
        Args:
            merchants: List of merchant names to categorize
            raise_on_error: If True, raises LLMError on failure (default True for bulk operations)
        
        Returns:
            List of categorization suggestions
            
        Raises:
            LLMError: If raise_on_error is True and an error occurs
        """
        if not merchants:
            return []
        
        function_schema = {
            "name": "categorize_merchants_bulk",
            "description": "Categorize multiple merchants and suggest matching patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categorizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "merchant": {"type": "string"},
                                "category": {"type": "string"},
                                "pattern": {"type": "string"},
                                "pattern_type": {"type": "string", "enum": ["keyword", "keyword_or", "regex"]},
                                "is_new_category": {"type": "boolean"}
                            },
                            "required": ["merchant", "category", "pattern", "pattern_type", "is_new_category"]
                        }
                    }
                },
                "required": ["categorizations"]
            }
        }
        
        merchant_list = "\n".join([f"- {m}" for m in merchants])
        user_prompt = f"Categorize these merchants:\n{merchant_list}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                functions=[function_schema],
                function_call={"name": "categorize_merchants_bulk"},
                temperature=0.0
            )
            
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                import json
                result = json.loads(function_call.arguments)
                return result.get("categorizations", [])
            return []
        except Exception as e:
            print(f"Error in bulk suggestion: {e}")
            if raise_on_error:
                raise parse_openai_error(e) from e
            # Fallback: try individual categorization (may also fail)
            return [
                {
                    "merchant": merchant,
                    "category": self.categorize_with_llm(merchant, raise_on_error=False),
                    "pattern": merchant.split()[0] if merchant else merchant,
                    "pattern_type": "keyword",
                    "is_new_category": False
                }
                for merchant in merchants
            ]

