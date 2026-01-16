"""Service for LLM-powered categorization using OpenAI."""
import os
import time
import logging
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

# Configure logger for LLM operations
logger = logging.getLogger("llm_service")
logger.setLevel(logging.INFO)

# Cost estimates per 1K tokens (as of 2024, adjust as needed)
MODEL_COSTS = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


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
    
    def __init__(
        self, 
        db: Session, 
        user_id: Optional[str] = None,
        workspace_id: Optional[int] = None,
        api_key: Optional[str] = None, 
        model: Optional[str] = None
    ):
        """Initialize LLM service.
        
        Args:
            db: Database session
            user_id: User ID to filter categories (if None, uses all categories)
            workspace_id: Workspace ID to filter categories (if None, uses user's categories)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model (defaults to OPENAI_MODEL env var or gpt-4o)
        """
        self.db = db
        self.user_id = user_id
        self.workspace_id = workspace_id
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
        """Build system prompt dynamically from user's categories."""
        # Filter categories by user and person if provided
        query = self.db.query(Category)
        if self.user_id:
            query = query.filter(Category.user_id == self.user_id)
        if self.workspace_id:
            query = query.filter(Category.workspace_id == self.workspace_id)
        
        categories = query.all()
        category_names = [c.name for c in categories] if categories else self.DEFAULT_CATEGORIES
        
        logger.info(f"📋 LLM initialized with {len(category_names)} categories for user={self.user_id}, person={self.workspace_id}")
        
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
            logger.error(f"❌ LLM categorize error for '{merchant[:50]}...': {e}")
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
            logger.debug("bulk_suggest_categories called with empty merchant list")
            return []
        
        logger.info(f"🤖 OpenAI API call: model={self.model}, merchants={len(merchants)}")
        
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
        
        start_time = time.time()
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
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract token usage from response
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            # Calculate estimated cost
            model_cost = MODEL_COSTS.get(self.model, MODEL_COSTS.get("gpt-4o"))
            estimated_cost = (input_tokens / 1000 * model_cost["input"]) + (output_tokens / 1000 * model_cost["output"])
            
            function_call_result = response.choices[0].message.function_call
            if function_call_result and function_call_result.arguments:
                import json
                result = json.loads(function_call_result.arguments)
                categorizations = result.get("categorizations", [])
                
                # Log detailed info about the OpenAI call
                logger.info(
                    f"✅ OpenAI response: "
                    f"latency={latency_ms:.0f}ms, "
                    f"tokens={{in:{input_tokens}, out:{output_tokens}, total:{total_tokens}}}, "
                    f"cost=${estimated_cost:.4f}, "
                    f"results={len(categorizations)}"
                )
                
                # Log what categories were suggested
                for cat in categorizations:
                    logger.info(f"   → '{cat.get('merchant', '')[:40]}...' → {cat.get('category')} (pattern: {cat.get('pattern')})")
                
                return categorizations
            
            logger.warning(f"⚠️ OpenAI returned no function call arguments after {latency_ms:.0f}ms")
            return []
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"❌ OpenAI error after {latency_ms:.0f}ms: {e}")
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

