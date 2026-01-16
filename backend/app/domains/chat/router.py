"""Chat API router for managing AI chat sessions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .service import ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: str


class AddContextRequest(BaseModel):
    date_range: dict
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    merchant: Optional[str] = None


class ContextEstimateRequest(BaseModel):
    date_range: dict
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    merchant: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str


class TokenUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class SendMessageResponse(BaseModel):
    response: str
    session_title: str
    token_usage: TokenUsageResponse


class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_calls: Optional[dict] = None
    created_at: str


class ContextSummary(BaseModel):
    total_income: float
    total_expenses: float
    net: float
    top_categories: List[dict]


class ContextResponse(BaseModel):
    context_id: str
    transaction_count: int
    limited: bool
    summary: dict


class ContextEstimateResponse(BaseModel):
    estimated_transactions: int
    actual_transactions: int
    estimated_tokens: int
    estimated_cost_usd: float
    limited: bool


class ContextInfoResponse(BaseModel):
    transaction_filters: Optional[dict] = None
    transaction_count: Optional[int] = None
    summary: Optional[ContextSummary] = None


class SessionContextResponse(BaseModel):
    transaction_filters: Optional[dict] = None
    transaction_count: Optional[int] = None
    transaction_summary: Optional[dict] = None
    include_categories: bool = False


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse]
    context: Optional[SessionContextResponse] = None


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: CreateSessionRequest, 
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Create a new chat session."""
    session = ChatService.create_session(ctx.db, ctx.user_id, request.title, ctx.workspace_id)
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        message_count=0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """List all chat sessions for the current user and active person."""
    sessions = ChatService.list_sessions(ctx.db, ctx.user_id, ctx.workspace_id)
    return [SessionResponse(**session) for session in sessions]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get a specific chat session with its messages and context."""
    # TODO: Add workspace_id support to ChatService.get_session
    session = ChatService.get_session(ctx.db, session_id, ctx.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return SessionDetailResponse(**session)


@router.put("/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str, 
    request: UpdateSessionRequest, 
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update a chat session's title."""
    # TODO: Add workspace_id support to ChatService.update_session
    session = ChatService.update_session(ctx.db, session_id, ctx.user_id, request.title)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    
    sessions_list = ChatService.list_sessions(ctx.db, ctx.user_id, ctx.workspace_id)
    message_count = next((s['message_count'] for s in sessions_list if s['id'] == session_id), 0)
    
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        message_count=message_count,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Delete a chat session."""
    # TODO: Add workspace_id support to ChatService.delete_session
    deleted = ChatService.delete_session(ctx.db, session_id, ctx.user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return None


@router.post("/sessions/{session_id}/context", response_model=ContextResponse)
def add_context(
    session_id: str, 
    request: AddContextRequest, 
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Add transaction context to a chat session."""
    try:
        # TODO: Add workspace_id support to ChatService.add_context
        context_info = ChatService.add_context(
            db=ctx.db, 
            session_id=session_id, 
            user_id=ctx.user_id,
            transaction_filters=request.model_dump(exclude_none=True)
        )
        return ContextResponse(**context_info)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/sessions/{session_id}/context", response_model=ContextInfoResponse)
def get_context(session_id: str, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get context for a chat session."""
    # TODO: Add workspace_id support to ChatService.get_context
    context = ChatService.get_context(ctx.db, session_id, ctx.user_id)
    if context is None:
        return ContextInfoResponse(transaction_filters=None, transaction_count=None, summary=None)
    
    summary_data = context.get('summary')
    summary = ContextSummary(**summary_data) if summary_data else None
    return ContextInfoResponse(
        transaction_filters=context.get('transaction_filters'),
        transaction_count=context.get('transaction_count'),
        summary=summary
    )


@router.delete("/sessions/{session_id}/context", status_code=status.HTTP_204_NO_CONTENT)
def remove_context(session_id: str, ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Remove context from a chat session."""
    # TODO: Add workspace_id support to ChatService.remove_context
    removed = ChatService.remove_context(ctx.db, session_id, ctx.user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context not found")
    return None


@router.post("/sessions/context/estimate", response_model=ContextEstimateResponse)
def estimate_context(
    request: ContextEstimateRequest, 
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Estimate the size of a context before adding it."""
    # TODO: Add workspace_id support to ChatService.estimate_context
    estimate = ChatService.estimate_context(
        db=ctx.db, 
        user_id=ctx.user_id, 
        transaction_filters=request.model_dump(exclude_none=True)
    )
    return ContextEstimateResponse(**estimate)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str, 
    request: SendMessageRequest, 
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Send a message to the AI assistant in a chat session."""
    try:
        # TODO: Add workspace_id support to ChatService.send_message
        result = ChatService.send_message(
            db=ctx.db, 
            session_id=session_id, 
            user_id=ctx.user_id, 
            message=request.message
        )
        return SendMessageResponse(
            response=result["response"],
            session_title=result["session_title"],
            token_usage=TokenUsageResponse(**result["token_usage"])
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing message: {str(e)}")
