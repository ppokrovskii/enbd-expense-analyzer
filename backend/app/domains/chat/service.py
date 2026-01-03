"""Chat service for managing chat sessions, messages, and context."""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import ChatSession, ChatMessage, ChatContext
from app.domains.transactions.models import Transaction
from app.domains.transactions.service import TransactionService
from .ai_tools import AITools
from .token_tracking import TokenTrackingService
import uuid
import json
import os
from openai import OpenAI


class ChatService:
    """Service for managing AI chat sessions."""
    
    MAX_CONTEXT_TRANSACTIONS = 1000
    
    @staticmethod
    def create_session(db: Session, user_id: str, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        if title is None:
            title = f"New Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        session = ChatSession(
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def list_sessions(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """List all chat sessions for a user."""
        sessions = db.query(
            ChatSession.id,
            ChatSession.title,
            ChatSession.created_at,
            ChatSession.updated_at,
            func.count(ChatMessage.id).label('message_count')
        ).outerjoin(
            ChatMessage, ChatSession.id == ChatMessage.session_id
        ).filter(
            ChatSession.user_id == user_id
        ).group_by(
            ChatSession.id, ChatSession.title, ChatSession.created_at, ChatSession.updated_at
        ).order_by(ChatSession.updated_at.desc()).all()
        
        return [
            {
                'id': str(session.id),
                'title': session.title,
                'message_count': session.message_count,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat()
            }
            for session in sessions
        ]
    
    @staticmethod
    def get_session(db: Session, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chat session with its messages and context."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return None
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_uuid
        ).order_by(ChatMessage.created_at.asc()).all()
        
        context = db.query(ChatContext).filter(
            ChatContext.session_id == session_uuid
        ).first()
        
        return {
            'id': str(session.id),
            'title': session.title,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'messages': [
                {
                    'id': str(msg.id),
                    'role': msg.role,
                    'content': msg.content,
                    'tool_calls': msg.tool_calls,
                    'created_at': msg.created_at.isoformat()
                }
                for msg in messages
            ],
            'context': {
                'transaction_filters': context.transaction_filters,
                'transaction_count': context.transaction_count,
                'transaction_summary': context.transaction_summary,
                'include_categories': context.include_categories
            } if context else None
        }
    
    @staticmethod
    def update_session(db: Session, session_id: str, user_id: str, title: str) -> Optional[ChatSession]:
        """Update a chat session's title."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return None
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        session.title = title
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def delete_session(db: Session, session_id: str, user_id: str) -> bool:
        """Delete a chat session."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return False
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        return True
    
    @staticmethod
    def add_context(
        db: Session,
        session_id: str,
        user_id: str,
        transaction_filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add transaction context to a chat session."""
        session_uuid = uuid.UUID(session_id)
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        filters = transaction_filters or {}
        date_range = filters.get('date_range', {})
        start_date = date.fromisoformat(date_range['from']) if date_range.get('from') else None
        end_date = date.fromisoformat(date_range['to']) if date_range.get('to') else None
        
        transactions, total = TransactionService.get_filtered_transactions(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=filters.get('categories'),
            accounts=filters.get('accounts'),
            merchant=filters.get('merchant'),
            exclude_transfers=True,
            page=1,
            page_size=ChatService.MAX_CONTEXT_TRANSACTIONS
        )
        
        summary = ChatService._build_transaction_summary(transactions)
        limited = total > ChatService.MAX_CONTEXT_TRANSACTIONS
        transaction_count = len(transactions)
        
        existing_context = db.query(ChatContext).filter(
            ChatContext.session_id == session_uuid
        ).first()
        
        if existing_context:
            existing_context.transaction_filters = transaction_filters
            existing_context.transaction_count = transaction_count
            existing_context.transaction_summary = summary
            existing_context.updated_at = datetime.utcnow()
            context = existing_context
        else:
            context = ChatContext(
                session_id=session_uuid,
                transaction_filters=transaction_filters,
                transaction_count=transaction_count,
                transaction_summary=summary,
                include_categories=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(context)
        
        db.commit()
        db.refresh(context)
        
        return {
            'context_id': str(context.id),
            'transaction_count': transaction_count,
            'limited': limited,
            'summary': summary
        }
    
    @staticmethod
    def get_context(db: Session, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get context for a chat session."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return None
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        context = db.query(ChatContext).filter(
            ChatContext.session_id == session_uuid
        ).first()
        
        if not context:
            return None
        
        return {
            'transaction_filters': context.transaction_filters,
            'transaction_count': context.transaction_count,
            'summary': context.transaction_summary
        }
    
    @staticmethod
    def remove_context(db: Session, session_id: str, user_id: str) -> bool:
        """Remove context from a chat session."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            return False
        
        session = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            return False
        
        context = db.query(ChatContext).filter(
            ChatContext.session_id == session_uuid
        ).first()
        
        if not context:
            return False
        
        db.delete(context)
        db.commit()
        return True
    
    @staticmethod
    def estimate_context(db: Session, user_id: str, transaction_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate the size of a context without adding it."""
        filters = transaction_filters or {}
        date_range = filters.get('date_range', {})
        start_date = date.fromisoformat(date_range['from']) if date_range.get('from') else None
        end_date = date.fromisoformat(date_range['to']) if date_range.get('to') else None
        
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        query = TransactionService.apply_base_filters(
            query,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=filters.get('categories'),
            accounts=filters.get('accounts'),
            merchant=filters.get('merchant'),
            exclude_transfers=True
        )
        
        total_count = query.count()
        limited_count = min(total_count, ChatService.MAX_CONTEXT_TRANSACTIONS)
        estimated_tokens = limited_count * 3
        estimated_cost = (estimated_tokens / 1000) * 0.005
        
        return {
            'estimated_transactions': total_count,
            'actual_transactions': limited_count,
            'estimated_tokens': estimated_tokens,
            'estimated_cost_usd': round(estimated_cost, 4),
            'limited': total_count > ChatService.MAX_CONTEXT_TRANSACTIONS
        }
    
    @staticmethod
    def _build_transaction_summary(transactions: List) -> Dict[str, Any]:
        """Build a summary of transactions for context."""
        if not transactions:
            return {'total_income': 0, 'total_expenses': 0, 'net': 0, 'top_categories': []}
        
        total_income = sum(float(t.amount_signed) for t in transactions if t.amount_signed and t.amount_signed > 0)
        total_expenses = sum(abs(float(t.amount_signed)) for t in transactions if t.amount_signed and t.amount_signed < 0)
        
        category_totals = {}
        for t in transactions:
            if t.amount_signed and t.amount_signed < 0:
                category = t.category or 'Other'
                category_totals[category] = category_totals.get(category, 0) + abs(float(t.amount_signed))
        
        top_categories = [
            {'name': cat, 'total': round(total, 2)}
            for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return {
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net': round(total_income - total_expenses, 2),
            'top_categories': top_categories
        }
    
    @staticmethod
    def send_message(db: Session, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """Send a message to the AI assistant and get a response."""
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise ValueError("Invalid session ID format")
        
        session_obj = db.query(ChatSession).filter(
            ChatSession.id == session_uuid,
            ChatSession.user_id == user_id
        ).first()
        
        if not session_obj:
            raise ValueError("Session not found")
        
        user_message = ChatMessage(
            session_id=session_uuid,
            role='user',
            content=message,
            created_at=datetime.utcnow()
        )
        db.add(user_message)
        db.commit()
        
        message_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_uuid).count()
        is_first_message = message_count == 1
        
        messages = ChatService._build_conversation_history(db, session_uuid, user_id)
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        client = OpenAI(api_key=api_key)
        
        if is_first_message:
            new_title = ChatService._generate_session_title(client, message)
            session_obj.title = new_title
            session_obj.updated_at = datetime.utcnow()
            db.commit()
        
        tools = AITools.get_tool_definitions()
        
        max_iterations = 5
        total_prompt_tokens = 0
        total_completion_tokens = 0
        assistant_responses = []
        
        for iteration in range(max_iterations):
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.7,
                max_tokens=1000
            )
            
            if response.usage:
                total_prompt_tokens += response.usage.prompt_tokens
                total_completion_tokens += response.usage.completion_tokens
            
            message_obj = response.choices[0].message
            
            if not message_obj.tool_calls:
                assistant_content = message_obj.content or ""
                assistant_msg = ChatMessage(
                    session_id=session_uuid,
                    role='assistant',
                    content=assistant_content,
                    created_at=datetime.utcnow()
                )
                db.add(assistant_msg)
                db.commit()
                assistant_responses.append({"role": "assistant", "content": assistant_content})
                break
            
            tool_calls_data = [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in message_obj.tool_calls
            ]
            
            assistant_msg = ChatMessage(
                session_id=session_uuid,
                role='assistant',
                content=message_obj.content or "",
                tool_calls={"calls": tool_calls_data},
                created_at=datetime.utcnow()
            )
            db.add(assistant_msg)
            db.commit()
            
            messages.append({
                "role": "assistant",
                "content": message_obj.content,
                "tool_calls": [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message_obj.tool_calls]
            })
            
            for tool_call in message_obj.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                tool_result = AITools.execute_tool(function_name, function_args, db, user_id)
                tool_response = json.dumps(tool_result)
                
                tool_msg = ChatMessage(
                    session_id=session_uuid,
                    role='tool',
                    content=tool_response,
                    tool_calls={"tool_call_id": tool_call.id, "name": function_name},
                    created_at=datetime.utcnow()
                )
                db.add(tool_msg)
                
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_response})
            
            db.commit()
        
        session_obj.updated_at = datetime.utcnow()
        db.commit()
        
        total_cost = (total_prompt_tokens / 1000 * 0.01) + (total_completion_tokens / 1000 * 0.03)
        
        TokenTrackingService.record_usage(
            db=db,
            user_id=user_id,
            session_id=session_id,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            cost_usd=total_cost
        )
        
        return {
            "response": assistant_responses[-1]["content"] if assistant_responses else "",
            "session_title": session_obj.title,
            "token_usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "cost_usd": round(total_cost, 6)
            }
        }
    
    @staticmethod
    def _generate_session_title(client: OpenAI, first_message: str) -> str:
        """Generate a concise title for the chat session."""
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate a very short title (max 6 words) for a financial chat. Return only the title."},
                    {"role": "user", "content": first_message}
                ],
                temperature=0.7,
                max_tokens=20
            )
            title = response.choices[0].message.content.strip().strip('"\'')
            return title[:50] if len(title) > 50 else title
        except Exception:
            return first_message[:50]
    
    @staticmethod
    def _build_conversation_history(db: Session, session_id: uuid.UUID, user_id: str) -> List[Dict[str, Any]]:
        """Build conversation history for OpenAI API."""
        messages = []
        
        system_message = """You are a helpful financial assistant analyzing the user's expense transactions.
You have access to tools that can query transaction data and analyze spending patterns.
Be concise, accurate, and helpful."""
        
        context = db.query(ChatContext).filter(ChatContext.session_id == session_id).first()
        if context:
            system_message += f"\n\nCurrent context: {context.transaction_count} transactions loaded"
            if context.transaction_filters:
                system_message += f" with filters: {json.dumps(context.transaction_filters)}"
        
        messages.append({"role": "system", "content": system_message})
        
        previous_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        
        for msg in previous_messages:
            if msg.role == 'tool':
                tool_data = msg.tool_calls or {}
                messages.append({"role": "tool", "tool_call_id": tool_data.get("tool_call_id", ""), "content": msg.content})
            elif msg.role == 'assistant' and msg.tool_calls:
                tool_calls = msg.tool_calls.get("calls", [])
                messages.append({
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [{"id": tc["id"], "type": tc["type"], "function": tc["function"]} for tc in tool_calls]
                })
            else:
                messages.append({"role": msg.role, "content": msg.content})
        
        return messages

