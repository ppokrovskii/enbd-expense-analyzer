"""LLM-powered categorization rule generation service."""
import openai
import json
import os
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from .models import Category


class LLMRuleService:
    """Service for generating categorization rules using LLM."""
    
    def __init__(self):
        """Initialize with OpenAI API key."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    async def generate_rule(
        self,
        db: Session,
        user_id: str,
        merchant: str,
        description: str,
        details: str,
        suggested_category: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict:
        """Generate a categorization rule using LLM."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        categories = db.query(Category).filter_by(user_id=user_id).all()
        category_list = [c.name for c in categories]
        
        prompt = self._build_rule_generation_prompt(
            merchant=merchant,
            description=description,
            details=details,
            available_categories=category_list,
            suggested_category=suggested_category,
            context=context
        )
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing financial transactions and creating categorization rules."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._validate_rule_result(result, category_list)
            
        except Exception as e:
            raise ValueError(f"Failed to generate rule: {str(e)}")
    
    def _build_rule_generation_prompt(
        self,
        merchant: str,
        description: str,
        details: str,
        available_categories: List[str],
        suggested_category: Optional[str],
        context: Optional[str]
    ) -> str:
        """Build the prompt for rule generation."""
        return f"""Analyze this transaction and create a categorization rule:

**Transaction Details:**
- Merchant: {merchant}
- Description: {description}
- Details: {details}
{f'- Context: {context}' if context else ''}

**Available Categories:**
{', '.join(available_categories)}

{f'**Suggested Category:** {suggested_category}' if suggested_category else ''}

**Response Format (JSON):**
{{
  "category": "CategoryName",
  "keywords": ["KEYWORD1", "KEYWORD2"],
  "exclude_keywords": ["REFUND", "REVERSAL"],
  "confidence": 0.95,
  "reasoning": "Brief explanation"
}}"""
    
    def _validate_rule_result(self, result: Dict, available_categories: List[str]) -> Dict:
        """Validate and normalize the LLM result."""
        if 'category' not in result:
            raise ValueError("LLM response missing 'category' field")
        
        keywords = result.get('keywords', [])
        if not isinstance(keywords, list):
            keywords = [keywords]
        
        exclude_keywords = result.get('exclude_keywords', [])
        if not isinstance(exclude_keywords, list):
            exclude_keywords = [exclude_keywords]
        
        category = result['category']
        if category not in available_categories and 'Other' in available_categories:
            category = 'Other'
        
        confidence = float(result.get('confidence', 0.7))
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'category': category,
            'keywords': keywords,
            'exclude_keywords': exclude_keywords,
            'confidence': confidence,
            'reasoning': result.get('reasoning', ''),
            'is_new_category': category not in available_categories
        }
    
    async def suggest_category_for_merchant(
        self,
        db: Session,
        user_id: str,
        merchant: str,
        sample_transactions: List[Dict]
    ) -> Dict:
        """Suggest a category for a merchant based on sample transactions."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        categories = db.query(Category).filter_by(user_id=user_id).all()
        category_list = [c.name for c in categories]
        
        samples_text = "\n".join([
            f"- {t.get('description', '')} | {t.get('details', '')} | Amount: {t.get('amount', '')}"
            for t in sample_transactions[:5]
        ])
        
        prompt = f"""Analyze these transactions from merchant "{merchant}":

**Sample Transactions:**
{samples_text}

**Available Categories:**
{', '.join(category_list)}

**Response (JSON):**
{{
  "category": "CategoryName",
  "confidence": 0.90,
  "reasoning": "Why this category fits"
}}"""
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a financial transaction categorization expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                'category': result.get('category', 'Other'),
                'confidence': float(result.get('confidence', 0.5)),
                'reasoning': result.get('reasoning', '')
            }
            
        except Exception as e:
            return {
                'category': 'Other',
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}'
            }

