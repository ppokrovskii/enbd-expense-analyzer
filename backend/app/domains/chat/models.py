"""SQLAlchemy models for the Chat domain."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, JSON, Boolean, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.shared.database import Base


class ChatSession(Base):
    """Chat session model for AI conversations."""
    
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String(50), nullable=False)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_chat_sessions_user_updated', 'user_id', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, workspace_id={self.workspace_id}, title={self.title})>"


class ChatMessage(Base):
    """Chat message model for conversation history."""
    
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)  # Store function calls if any
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_chat_messages_session_created', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"


class ChatContext(Base):
    """Chat context model for transaction and category data injection."""
    
    __tablename__ = "chat_contexts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True)
    transaction_filters = Column(JSON, nullable=True)  # date_range, categories, accounts
    transaction_count = Column(Integer, nullable=True)
    transaction_summary = Column(JSON, nullable=True)  # Aggregated stats
    include_categories = Column(Boolean, server_default='false', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('session_id', name='uq_chat_contexts_session_id'),
        Index('ix_chat_contexts_session_id', 'session_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ChatContext(id={self.id}, session_id={self.session_id}, transaction_count={self.transaction_count})>"


class TokenUsage(Base):
    """Token usage tracking for AI chat."""
    
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(String(50), nullable=False)
    workspace_id = Column(Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='SET NULL'), nullable=True)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_token_usage_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TokenUsage(id={self.id}, user_id={self.user_id}, total_tokens={self.total_tokens}, cost_usd={self.cost_usd})>"

