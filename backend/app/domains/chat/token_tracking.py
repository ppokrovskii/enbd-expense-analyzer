"""Token usage tracking service for monitoring AI costs."""
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import TokenUsage
import uuid


class TokenTrackingService:
    """Service for tracking and analyzing token usage."""
    
    @staticmethod
    def record_usage(
        db: Session,
        user_id: str,
        session_id: Optional[str],
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float
    ) -> TokenUsage:
        """Record token usage for a user/session."""
        session_uuid = uuid.UUID(session_id) if session_id else None
        
        token_usage = TokenUsage(
            user_id=user_id,
            session_id=session_uuid,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=Decimal(str(cost_usd)),
            created_at=datetime.utcnow()
        )
        
        db.add(token_usage)
        db.commit()
        db.refresh(token_usage)
        
        return token_usage
    
    @staticmethod
    def get_user_usage_summary(db: Session, user_id: str) -> Dict[str, Any]:
        """Get token usage summary for a user."""
        result = db.query(TokenUsage).filter(TokenUsage.user_id == user_id).with_entities(
            func.sum(TokenUsage.prompt_tokens).label('total_prompt'),
            func.sum(TokenUsage.completion_tokens).label('total_completion'),
            func.sum(TokenUsage.total_tokens).label('total_tokens'),
            func.sum(TokenUsage.cost_usd).label('total_cost'),
            func.count(TokenUsage.id).label('request_count')
        ).first()
        
        return {
            'total_prompt_tokens': int(result.total_prompt or 0),
            'total_completion_tokens': int(result.total_completion or 0),
            'total_tokens': int(result.total_tokens or 0),
            'total_cost_usd': float(result.total_cost or 0),
            'request_count': result.request_count or 0
        }

