"""Chat API router for managing AI chat sessions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_user_id
from app.services.chat_service import ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    """Request model for creating a chat session."""
    title: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Request model for updating a chat session."""
    title: str


class AddContextRequest(BaseModel):
    """Request model for adding transaction context."""
    date_range: dict  # {'from': 'YYYY-MM-DD', 'to': 'YYYY-MM-DD'}
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    merchant: Optional[str] = None


class ContextEstimateRequest(BaseModel):
    """Request model for estimating context size."""
    date_range: dict
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    merchant: Optional[str] = None


class ContextResponse(BaseModel):
    """Response model for added context."""
    context_id: str
    transaction_count: int
    limited: bool
    summary: dict


class ContextEstimateResponse(BaseModel):
    """Response model for context estimation."""
    estimated_transactions: int
    actual_transactions: int
    estimated_tokens: int
    estimated_cost_usd: float
    limited: bool


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    message: str


class TokenUsageResponse(BaseModel):
    """Response model for token usage."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class SendMessageResponse(BaseModel):
    """Response model for sending a message."""
    response: str
    session_title: str  # Include updated session title
    token_usage: TokenUsageResponse


class SessionResponse(BaseModel):
    """Response model for a chat session summary."""
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Response model for a chat message."""
    id: str
    role: str
    content: str
    tool_calls: Optional[dict] = None
    created_at: str


class ContextSummary(BaseModel):
    """Summary statistics for context."""
    total_income: float
    total_expenses: float
    net: float
    top_categories: List[dict]


class ContextInfoResponse(BaseModel):
    """Response model for context information."""
    transaction_filters: Optional[dict] = None
    transaction_count: Optional[int] = None
    summary: Optional[ContextSummary] = None


class SessionContextResponse(BaseModel):
    """Response model for chat context in session detail."""
    transaction_filters: Optional[dict] = None
    transaction_count: Optional[int] = None
    transaction_summary: Optional[dict] = None
    include_categories: bool = False


class SessionDetailResponse(BaseModel):
    """Response model for a full chat session with messages."""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse]
    context: Optional[SessionContextResponse] = None


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Create a new chat session.
    
    Args:
        request: Optional title for the session
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Created session details
    """
    session = ChatService.create_session(db, user_id, request.title)
    
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        message_count=0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    List all chat sessions for the current user.
    
    Args:
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        List of session summaries
    """
    sessions = ChatService.list_sessions(db, user_id)
    return [SessionResponse(**session) for session in sessions]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Get a specific chat session with its messages and context.
    
    Args:
        session_id: Session UUID
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Full session details with messages
    """
    session = ChatService.get_session(db, session_id, user_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return SessionDetailResponse(**session)


@router.put("/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Update a chat session's title.
    
    Args:
        session_id: Session UUID
        request: New title
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Updated session details
    """
    session = ChatService.update_session(db, session_id, user_id, request.title)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Get message count
    sessions_list = ChatService.list_sessions(db, user_id)
    message_count = next(
        (s['message_count'] for s in sessions_list if s['id'] == session_id),
        0
    )
    
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        message_count=message_count,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat()
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Delete a chat session.
    
    Args:
        session_id: Session UUID
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        No content on success
    """
    deleted = ChatService.delete_session(db, session_id, user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return None


@router.post("/sessions/{session_id}/context", response_model=ContextResponse)
def add_context(
    session_id: str,
    request: AddContextRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Add transaction context to a chat session.
    
    Args:
        session_id: Session UUID
        request: Transaction filters
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Context info including count and summary
    """
    try:
        context_info = ChatService.add_context(
            db=db,
            session_id=session_id,
            user_id=user_id,
            transaction_filters=request.dict(exclude_none=True)
        )
        return ContextResponse(**context_info)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/sessions/{session_id}/context", response_model=ContextInfoResponse)
def get_context(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Get context for a chat session.
    
    Args:
        session_id: Session UUID
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Context info or null
    """
    context = ChatService.get_context(db, session_id, user_id)
    if context is None:
        # Return empty response, not None
        return ContextInfoResponse(
            transaction_filters=None,
            transaction_count=None,
            summary=None
        )
    
    # Convert summary to proper model
    summary_data = context.get('summary')
    summary = ContextSummary(**summary_data) if summary_data else None
    
    return ContextInfoResponse(
        transaction_filters=context.get('transaction_filters'),
        transaction_count=context.get('transaction_count'),
        summary=summary
    )


@router.delete("/sessions/{session_id}/context", status_code=status.HTTP_204_NO_CONTENT)
def remove_context(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Remove context from a chat session.
    
    Args:
        session_id: Session UUID
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        No content on success
    """
    removed = ChatService.remove_context(db, session_id, user_id)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Context not found"
        )
    
    return None


@router.post("/sessions/context/estimate", response_model=ContextEstimateResponse)
def estimate_context(
    request: ContextEstimateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Estimate the size of a context before adding it.
    
    Args:
        request: Transaction filters
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Estimation including token count and cost
    """
    estimate = ChatService.estimate_context(
        db=db,
        user_id=user_id,
        transaction_filters=request.dict(exclude_none=True)
    )
    return ContextEstimateResponse(**estimate)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Send a message to the AI assistant in a chat session.
    
    Args:
        session_id: Session UUID
        request: Message content
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        AI response with token usage
    """
    try:
        result = ChatService.send_message(
            db=db,
            session_id=session_id,
            user_id=user_id,
            message=request.message
        )
        
        return SendMessageResponse(
            response=result["response"],
            session_title=result["session_title"],
            token_usage=TokenUsageResponse(**result["token_usage"])
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the error in production
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )

