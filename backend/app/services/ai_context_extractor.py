"""AI Context Extractor Service for natural language filter extraction."""
import openai
import json
import os
from typing import Dict, Optional
from datetime import datetime, timedelta


class AIContextExtractor:
    """Extract filter context from natural language queries."""
    
    def __init__(self):
        """Initialize the AI context extractor."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        openai.api_key = self.openai_api_key
    
    async def extract_filters(self, query: str) -> Dict:
        """
        Use LLM to extract filters from natural language query.
        
        Args:
            query: Natural language query from user
            
        Returns:
            Dictionary with extracted filters: merchant, start_date, end_date, categories
        """
        # Get current date for relative date calculations
        today = datetime.now()
        current_year = today.year
        current_month = today.month
        
        prompt = f"""Extract transaction filter parameters from this query:
"{query}"

Today's date is {today.strftime('%Y-%m-%d')}.

Return JSON with:
- merchant: string or null (any merchant/shop name mentioned)
- start_date: ISO date string (YYYY-MM-DD) or null
- end_date: ISO date string (YYYY-MM-DD) or null  
- categories: list of category names or []

Important date calculations:
- "last month" means previous calendar month
- "this month" means current calendar month
- "October" with no year means October {current_year}
- "last 30 days" means 30 days before today
- "this year" means January 1 to today of {current_year}

Common categories: Groceries, Transport, Food & Dining, Shopping, Entertainment, Healthcare, Utilities, Technology Subscriptions, Telecommunications

Examples:
"coffee in October" -> {{"merchant": "coffee", "start_date": "{current_year}-10-01", "end_date": "{current_year}-10-31", "categories": []}}
"groceries last month" -> {{"merchant": null, "start_date": "YYYY-MM-01", "end_date": "YYYY-MM-DD", "categories": ["Groceries"]}}
"how much on transport this year" -> {{"merchant": null, "start_date": "{current_year}-01-01", "end_date": "{today.strftime('%Y-%m-%d')}", "categories": ["Transport"]}}
"starbucks purchases" -> {{"merchant": "starbucks", "start_date": null, "end_date": null, "categories": []}}

Return ONLY valid JSON, no markdown or explanations.
"""
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Ensure all keys exist
            return {
                "merchant": result.get("merchant"),
                "start_date": result.get("start_date"),
                "end_date": result.get("end_date"),
                "categories": result.get("categories", [])
            }
            
        except Exception as e:
            print(f"Error extracting filters: {e}")
            # Return empty filters on error
            return {
                "merchant": None,
                "start_date": None,
                "end_date": None,
                "categories": []
            }
    
    def has_filters(self, filters: Dict) -> bool:
        """Check if any meaningful filters were extracted."""
        return bool(
            filters.get("merchant") or
            filters.get("start_date") or
            filters.get("end_date") or
            filters.get("categories")
        )

