"""Service for LLM-powered categorization using OpenAI."""
import os
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models import Transaction, LLMCache, Category

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
        """
        Initialize LLM service.
        
        Args:
            db: Database session to fetch user categories
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to OPENAI_MODEL env var or gpt-4o)
        """
        self.db = db
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        # Build system prompt from user's categories
        self.system_prompt = self._build_system_prompt()
        
        # Lazy import to avoid dependency when not using LLM
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt dynamically from database categories."""
        # Fetch categories from database
        categories = self.db.query(Category).all()
        category_names = [c.name for c in categories] if categories else self.DEFAULT_CATEGORIES
        
        # Ensure "Other" is always present
        if "Other" not in category_names:
            category_names.append("Other")
        
        # Build category list
        category_list = "\n".join([f"- {cat}" for cat in sorted(category_names)])
        
        # Build standard MCC category list for reference
        standard_categories_list = "\n".join([f"- {cat}" for cat in sorted(self.STANDARD_MCC_CATEGORIES)])
        
        return f"""You are an expense categorization assistant with knowledge of businesses, merchants, and services worldwide. Your job is to categorize merchant/transaction descriptions into appropriate categories.

**YOUR TASK:**
1. **Analyze the merchant name** to understand what type of business it is
2. **Use your knowledge** of companies, brands, and business types to categorize accurately
3. **Consider context clues** in the name (e.g., "CLINIC", "PHARMACY", "RESTAURANT", "SUPERMARKET")
4. **Think about common patterns**: 
   - Medical facilities often have "CLINIC", "HOSPITAL", "MEDICAL", "PHARMACY", "DENTAL"
   - Food businesses use "RESTAURANT", "CAFE", "BAKERY", "FOOD"
   - Retail stores use "STORE", "SHOP", "MARKET"
   - Technology companies often end in ".AI", ".COM", "TECH"

**USER'S CURRENT CATEGORIES:**
{category_list}

**STANDARD CATEGORIES (MCC-based) FOR REFERENCE:**
If none of the user's categories fit well, you can suggest creating a new category from this standard list:
{standard_categories_list}

**IMPORTANT**: 
- **Use your knowledge base** to identify what type of business each merchant is
- For example: "AJA INTERNATIONAL" → If you know this is a healthcare/medical facility in UAE, categorize as Healthcare
- Prefer using the user's existing categories when possible
- If a merchant doesn't fit well into any existing category, you may suggest a NEW category from the standard list above
- To suggest a new category, use the exact name from the standard list
- Only suggest "Other" if truly none of the standard categories fit

**Critical Rules for Transfer Detection:**

1. **INCOMING transfers** - Money YOU received:
   - Contains "TRANSFER FROM", "FASTPAY TRANSFER FROM", "MOBILE BANKING TRANSFER FROM"
   - Person's name followed by account/mobile number
   - Salary/payroll payments should be "Salary" not "Incoming Transfer"

2. **OUTGOING transfers** - Money YOU sent:
   - Contains "TRANSFER TO", "FASTPAY TRANSFER TO", "MOBILE BANKING TRANSFER TO"
   - Payment to account numbers (e.g., "AE12345...")
   - Person's name as recipient

3. **Account number patterns to IGNORE:**
   - Descriptions with "AE" followed by numbers are account numbers (e.g., "AE21026000021...")
   - Masked account numbers with asterisks (e.g., "AE620260001******935001")
   - These transfers should be categorized by direction (FROM=Incoming, TO=Outgoing)

**Rule Pattern Formats:**
When suggesting how to categorize merchants, you can suggest rules in these formats:

1. **Simple Keyword**: "RESTAURANT" (matches any transaction containing this word)
   - Use for single, distinctive words
   - Example: "CARREFOUR" catches all Carrefour transactions

2. **Keyword OR**: "DELIVEROO|TALABAT|ZOMATO" (matches any of these keywords)
   - Use for related merchants or variations
   - Example: "AMAZON|NOON" catches both Amazon and Noon

3. **Regex**: "^AMAZON\\..*DUBAI$" (advanced pattern matching)
   - Use only for complex patterns requiring precision
   - Example: "^DU\\s+(TELECOM|UAE)" for Du telecom variations

**Prefer simple keywords when possible. Use Keyword OR for related merchants. Use Regex only for complex patterns.**

**Examples:**
- "CARREFOUR HYPERMARKET" → Groceries (rule: "CARREFOUR")
- "UBER TRIP" or "CAREEM" → Transport (rule: "UBER|CAREEM")
- "AIRALO" → Telecommunications (rule: "AIRALO")
- "LRIL ONLINE" → Shopping (rule: "LRIL")
- "KARTINA.TV" → Entertainment (rule: "KARTINA")
- "SUNO.AI" or "TUNECORE" → Technology Subscriptions (rule: "SUNO|TUNECORE")
- "PAUL BAKERY" or "TEXAS DE BRAZ" → Food & Dining (rule: "PAUL|TEXAS DE BRAZ")
- "MICROSOFT 365" or "CURSOR.COM" → Technology Subscriptions (rule: "MICROSOFT|CURSOR")
- "DU TELECOM" or "ETISALAT" → Telecommunications (rule: "DU TELECOM|ETISALAT")
- "DUBAI ELECTRICITY" or "DEWA" → Utilities (rule: "DUBAI ELECTRICITY|DEWA")
- "DTB SALARY" → Salary (rule: "DTB")
- "MOBILE BANKING TRANSFER FROM AE620260001******935001" → Incoming Transfer (rule: "TRANSFER FROM")
- "MOBILE BANKING TRANSFER TO AE21026000021******5003" → Outgoing Transfer (rule: "TRANSFER TO")
- "FASTPAY TRANSFER FROM JOHN DOE MOBILE NO.00971..." → Incoming Transfer (rule: "FASTPAY TRANSFER FROM")
- "FASTPAY TRANSFER TO MARIA SMITH" → Outgoing Transfer (rule: "FASTPAY TRANSFER TO")

**Important:** Ignore account numbers and masked digits when categorizing. Focus on the direction (FROM vs TO) and transaction type.

Return ONLY the category name, nothing else. Choose from the available categories listed above."""
    
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

    def bulk_suggest_categories(self, merchants: List[str]) -> List[dict]:
        """
        Get AI suggestions for multiple merchants at once using OpenAI function calling.
        
        Args:
            merchants: List of merchant names
        
        Returns:
            List of dictionaries with structure:
            {
                'merchant': str,
                'category': str,
                'pattern': str,
                'pattern_type': str  # 'keyword', 'keyword_or', or 'regex'
            }
        """
        if not merchants:
            return []
        
        # Define the function schema for OpenAI
        function_schema = {
            "name": "categorize_merchants_bulk",
            "description": "Categorize multiple merchants and suggest matching patterns. Can suggest new categories from standard MCC list if user's categories don't fit well.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categorizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "merchant": {
                                    "type": "string",
                                    "description": "The merchant name being categorized"
                                },
                                "category": {
                                    "type": "string",
                                    "description": "The suggested category - use existing user category OR suggest a new one from standard MCC categories if it fits better"
                                },
                                "pattern": {
                                    "type": "string",
                                    "description": "A keyword or pattern to match this merchant (e.g., 'CARREFOUR', 'UBER|CAREEM', or regex)"
                                },
                                "pattern_type": {
                                    "type": "string",
                                    "enum": ["keyword", "keyword_or", "regex"],
                                    "description": "Type of pattern: keyword (simple), keyword_or (multiple keywords with |), or regex"
                                },
                                "is_new_category": {
                                    "type": "boolean",
                                    "description": "True if suggesting a new category from standard MCC list, False if using existing user category"
                                }
                            },
                            "required": ["merchant", "category", "pattern", "pattern_type", "is_new_category"]
                        }
                    }
                },
                "required": ["categorizations"]
            }
        }
        
        # Build the prompt
        merchant_list = "\n".join([f"- {m}" for m in merchants])
        user_prompt = f"""Analyze these merchants and suggest categories and matching patterns.

**IMPORTANT**: Use your knowledge of businesses, brands, and services to accurately identify what each merchant does.

**MERCHANTS TO CATEGORIZE:**
{merchant_list}

**YOUR APPROACH:**
1. **Identify the business type** - Use your knowledge base to understand what each merchant actually does
   - Example: "AJA INTERNATIONAL" → You know this is a medical/healthcare facility in Dubai
   - Example: "CARREFOUR" → You know this is a supermarket chain
   - Example: "DELIVEROO" → You know this is a food delivery service
2. **Choose the best category** - Prefer user's existing categories, but suggest NEW from standard MCC list if significantly better fit
3. **Set 'is_new_category'** to true if suggesting a category not in user's current list
4. **Create matching pattern** - Simple, effective keyword/pattern for similar transactions
5. **Pattern type** - Use 'keyword' for simple, 'keyword_or' for alternatives (A|B|C), 'regex' only when necessary

**EXAMPLES:**
- Medical clinic with unclear name → Healthcare (use your knowledge to identify it's medical)
- "LULU HYPERMARKET" → Supermarkets (even if user only has "Shopping", suggest the more specific category)
- "ZOMATO" → Food Delivery (if user has "Food & Dining", consider if "Food Delivery" is better)
- "ANYTIME FITNESS" → Fitness & Gym (suggest new if user doesn't have fitness category)

**Remember**: You have training data about businesses worldwide - use it!"""
        
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
            
            # Extract function call result
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                import json
                result = json.loads(function_call.arguments)
                return result.get("categorizations", [])
            else:
                print("No function call result from OpenAI")
                return []
        
        except Exception as e:
            print(f"Error in bulk suggestion: {e}")
            # Fallback: use simple categorization
            return [
                {
                    "merchant": merchant,
                    "category": self.categorize_with_llm(merchant),
                    "pattern": merchant.split()[0] if merchant else merchant,
                    "pattern_type": "keyword",
                    "is_new_category": False  # Default to False in fallback
                }
                for merchant in merchants
            ]

