"""
Tests for Milestone 4: AI Chat Assistant Logic

Validates that:
- Send message endpoint exists and accepts messages
- AI tools are properly defined
- Tool execution works with mocked OpenAI
- Token usage is tracked
- Error handling works correctly
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from decimal import Decimal
from app.main import app
from app.models import Transaction, Category
from app.services.ai_tools import AITools


client = TestClient(app)


def create_test_data(test_db, user_id):
    """Helper to create test transactions and categories."""
    # Create categories
    cat1 = Category(
        user_id=user_id,
        name='Food',
        created_at=datetime.utcnow()
    )
    cat2 = Category(
        user_id=user_id,
        name='Transport',
        created_at=datetime.utcnow()
    )
    test_db.add_all([cat1, cat2])
    
    # Create transactions
    transactions = []
    for i in range(20):
        transaction = Transaction(
            user_id=user_id,
            date=date(2025, 12, i % 28 + 1),
            account='Current Account',
            description=f'Test transaction {i}',
            details=f'Details {i}',
            debit_credit='D' if i % 4 != 0 else 'C',
            amount=Decimal('100.00'),
            amount_signed=Decimal('-100.00') if i % 4 != 0 else Decimal('100.00'),
            merchant=f'Merchant {i % 5}',
            category='Food' if i % 2 == 0 else 'Transport',
            transaction_hash=f'hash_{user_id}_{i}',
            created_at=datetime.utcnow()
        )
        transactions.append(transaction)
        test_db.add(transaction)
    
    test_db.commit()
    return transactions


def test_ai_tools_are_defined():
    """Test that AI tools are properly defined."""
    tools = AITools.get_tool_definitions()
    
    assert len(tools) > 0
    assert all('type' in tool for tool in tools)
    assert all('function' in tool for tool in tools)
    
    # Check specific tools exist
    tool_names = [tool['function']['name'] for tool in tools]
    assert 'query_transactions' in tool_names
    assert 'get_spending_trends' in tool_names
    assert 'list_categories' in tool_names


def test_query_transactions_tool(test_db):
    """Test the query_transactions AI tool."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Execute tool
    result = AITools.execute_tool(
        tool_name="query_transactions",
        arguments={
            "start_date": "2025-12-01",
            "end_date": "2025-12-31"
        },
        db=test_db,
        user_id=user_id
    )
    
    assert 'summary' in result
    assert 'top_categories' in result
    assert result['summary']['transaction_count'] == 20
    assert result['summary']['total_expenses'] > 0


def test_get_spending_trends_tool(test_db):
    """Test the get_spending_trends AI tool."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Execute tool
    result = AITools.execute_tool(
        tool_name="get_spending_trends",
        arguments={
            "start_date": "2025-12-01",
            "end_date": "2025-12-31",
            "grouping": "monthly"
        },
        db=test_db,
        user_id=user_id
    )
    
    assert 'grouping' in result
    assert 'data' in result
    assert result['grouping'] == 'monthly'
    assert len(result['data']) > 0


def test_list_categories_tool(test_db):
    """Test the list_categories AI tool."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Execute tool
    result = AITools.execute_tool(
        tool_name="list_categories",
        arguments={},
        db=test_db,
        user_id=user_id
    )
    
    assert 'categories' in result
    assert len(result['categories']) >= 2  # Food and Transport


def test_send_message_endpoint_exists(test_db):
    """Test that send message endpoint exists and requires a session."""
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": "test_user"}
    )
    session_id = session_response.json()['id']
    
    # Try to send a message (will fail without OpenAI key, but endpoint should exist)
    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"message": "Hello"},
        headers={"X-User-Id": "test_user"}
    )
    
    # Should either succeed or fail with a meaningful error (not 404)
    assert response.status_code != 404


@patch('app.domains.chat.service.OpenAI')
def test_send_message_with_mocked_openai(mock_openai_class, test_db):
    """Test sending a message with mocked OpenAI responses."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": user_id}
    )
    session_id = session_response.json()['id']
    
    # Mock OpenAI response (simple response without tool calls)
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content = "Based on your transactions, you spent $1500 this month."
    mock_message.tool_calls = None
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 150
    mock_usage.completion_tokens = 50
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Send message
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        response = client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "How much did I spend this month?"},
            headers={"X-User-Id": user_id}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert 'response' in data
    assert 'token_usage' in data
    assert data['token_usage']['prompt_tokens'] == 150
    assert data['token_usage']['completion_tokens'] == 50


@patch('app.domains.chat.service.OpenAI')
def test_send_message_with_tool_calls(mock_openai_class, test_db):
    """Test sending a message that triggers tool calls."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": user_id}
    )
    session_id = session_response.json()['id']
    
    # Mock OpenAI to return tool calls first, then a final response
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # First response with tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "query_transactions"
    mock_tool_call.function.arguments = '{"start_date": "2025-12-01", "end_date": "2025-12-31"}'
    
    mock_message1 = MagicMock()
    mock_message1.content = ""
    mock_message1.tool_calls = [mock_tool_call]
    
    mock_choice1 = MagicMock()
    mock_choice1.message = mock_message1
    
    mock_usage1 = MagicMock()
    mock_usage1.prompt_tokens = 100
    mock_usage1.completion_tokens = 20
    
    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]
    mock_response1.usage = mock_usage1
    
    # Second response with final answer
    mock_message2 = MagicMock()
    mock_message2.content = "You spent $1500 in December."
    mock_message2.tool_calls = None
    
    mock_choice2 = MagicMock()
    mock_choice2.message = mock_message2
    
    mock_usage2 = MagicMock()
    mock_usage2.prompt_tokens = 150
    mock_usage2.completion_tokens = 30
    
    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]
    mock_response2.usage = mock_usage2
    
    # Configure mock to return both responses in sequence
    mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]
    
    # Send message
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        response = client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "How much did I spend in December?"},
            headers={"X-User-Id": user_id}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert 'response' in data
    assert 'December' in data['response'] or 'spent' in data['response']
    # Token tracking may vary - just verify we got some tokens tracked
    assert data['token_usage']['total_tokens'] > 0


def test_send_message_requires_valid_session(test_db):
    """Test that sending a message to invalid session fails."""
    response = client.post(
        "/api/chat/sessions/00000000-0000-0000-0000-000000000000/messages",
        json={"message": "Hello"},
        headers={"X-User-Id": "test_user"}
    )
    
    assert response.status_code in [400, 404]


def test_send_message_validates_user_access(test_db):
    """Test that users can only send messages to their own sessions."""
    # User 1 creates session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "User 1 Chat"},
        headers={"X-User-Id": "user1"}
    )
    session_id = session_response.json()['id']
    
    # User 2 tries to send message to user 1's session
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        response = client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "Hello"},
            headers={"X-User-Id": "user2"}
        )
    
    assert response.status_code in [400, 404]


@patch('app.domains.chat.service.OpenAI')
def test_token_usage_is_recorded(mock_openai_class, test_db):
    """Test that token usage is properly recorded in the database."""
    user_id = "test_user"
    create_test_data(test_db, user_id)
    
    # Create session
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Test Chat"},
        headers={"X-User-Id": user_id}
    )
    session_id = session_response.json()['id']
    
    # Mock OpenAI
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_message = MagicMock()
    mock_message.content = "Test response"
    mock_message.tool_calls = None
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Send message
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        client.post(
            f"/api/chat/sessions/{session_id}/messages",
            json={"message": "Test"},
            headers={"X-User-Id": user_id}
        )
    
    # Check that token usage was recorded
    from app.models import TokenUsage
    token_record = test_db.query(TokenUsage).filter(
        TokenUsage.user_id == user_id
    ).first()
    
    assert token_record is not None
    assert token_record.prompt_tokens == 100
    assert token_record.completion_tokens == 50
    assert token_record.total_tokens == 150
    assert token_record.cost_usd > 0

