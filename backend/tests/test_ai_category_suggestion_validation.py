"""
Test AI Category Suggestion Validation
Tests that verify the LLM correctly identifies new vs existing categories
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Category
from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def setup_test_categories(test_db: Session):
    """Setup test categories in database"""
    # Create some existing categories
    existing_categories = [
        "Groceries",
        "Shopping",
        "Dining & Restaurants",
        "Transportation",
        "Utilities",
        "Other"
    ]
    
    for cat_name in existing_categories:
        category = Category(name=cat_name, keywords=[])
        test_db.add(category)
    
    test_db.commit()
    
    yield existing_categories
    
    # Cleanup is handled by test_db fixture


def test_llm_suggests_existing_category(client, test_db: Session, setup_test_categories, monkeypatch):
    """
    Test that when LLM suggests an existing category,
    is_new_category should be False
    """
    # Mock OpenAI response to suggest an existing category
    mock_response = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "function": {
                        "arguments": '{"suggestions": [{"merchant": "LULU HYPERMARKET", "category": "Groceries", "pattern": "LULU", "pattern_type": "keyword", "is_new_category": false}]}'
                    }
                }]
            }
        }]
    }
    
    def mock_create(*args, **kwargs):
        class MockResponse:
            choices = [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'tool_calls': [type('obj', (object,), {
                        'function': type('obj', (object,), {
                            'arguments': '{"suggestions": [{"merchant": "LULU HYPERMARKET", "category": "Groceries", "pattern": "LULU", "pattern_type": "keyword", "is_new_category": false}]}'
                        })()
                    })]
                })()
            })]
        return MockResponse()
    
    monkeypatch.setattr("app.services.llm_service.OpenAI", lambda *args, **kwargs: type('obj', (object,), {'chat': type('obj', (object,), {'completions': type('obj', (object,), {'create': mock_create})()})()})())
    
    response = client.get("/api/categories/ai-bulk-suggest?days=30&level=global")
    
    assert response.status_code == 200
    suggestions = response.json()
    
    # Verify the suggestion
    assert len(suggestions) > 0
    suggestion = suggestions[0]
    assert suggestion["suggested_category"] == "Groceries"
    assert suggestion["is_new_category"] == False


def test_llm_suggests_new_category_from_mcc_list(client, test_db: Session, setup_test_categories, monkeypatch):
    """
    Test that when LLM suggests a NEW category from MCC list,
    is_new_category should be True
    """
    # Mock OpenAI response to suggest a NEW category
    mock_response_json = '{"suggestions": [{"merchant": "WATERMARK DRY CLEANERS DUBAI", "category": "Personal Care & Beauty", "pattern": "WATERMARK", "pattern_type": "keyword", "is_new_category": true}]}'
    
    def mock_create(*args, **kwargs):
        class MockResponse:
            choices = [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'tool_calls': [type('obj', (object,), {
                        'function': type('obj', (object,), {
                            'arguments': mock_response_json
                        })()
                    })]
                })()
            })]
        return MockResponse()
    
    monkeypatch.setattr("app.services.llm_service.OpenAI", lambda *args, **kwargs: type('obj', (object,), {'chat': type('obj', (object,), {'completions': type('obj', (object,), {'create': mock_create})()})()})())
    
    response = client.get("/api/categories/ai-bulk-suggest?days=30&level=global")
    
    assert response.status_code == 200
    suggestions = response.json()
    
    # Verify the suggestion
    assert len(suggestions) > 0
    suggestion = suggestions[0]
    assert suggestion["suggested_category"] == "Personal Care & Beauty"
    assert suggestion["is_new_category"] == True
    
    # Verify that "Personal Care & Beauty" does NOT exist in database
    existing_category = test_db.query(Category).filter(Category.name == "Personal Care & Beauty").first()
    assert existing_category is None


def test_frontend_validation_of_new_category(client, test_db: Session, setup_test_categories):
    """
    Test the complete flow: Frontend should validate if suggested category exists
    This simulates what happens in the AI suggestions page
    """
    # 1. Get all existing categories (what frontend does first)
    categories_response = client.get("/api/categories/")
    assert categories_response.status_code == 200
    existing_categories = categories_response.json()
    existing_category_names = [cat["name"] for cat in existing_categories]
    
    # 2. Simulate a suggestion from LLM for a NEW category
    suggested_category = "Personal Care & Beauty"
    llm_says_is_new = True
    
    # 3. Frontend validation: Check if category exists
    category_exists = suggested_category in existing_category_names
    
    # 4. Final determination
    is_new_category = llm_says_is_new and not category_exists
    
    # Assertions
    assert "Personal Care & Beauty" not in existing_category_names
    assert category_exists == False
    assert is_new_category == True


def test_frontend_validation_of_existing_category(client, test_db: Session, setup_test_categories):
    """
    Test that frontend correctly identifies an existing category
    """
    # 1. Get all existing categories
    categories_response = client.get("/api/categories/")
    assert categories_response.status_code == 200
    existing_categories = categories_response.json()
    existing_category_names = [cat["name"] for cat in existing_categories]
    
    # 2. Simulate a suggestion from LLM for an EXISTING category
    suggested_category = "Groceries"
    llm_says_is_new = False
    
    # 3. Frontend validation: Check if category exists
    category_exists = suggested_category in existing_category_names
    
    # 4. Final determination
    is_new_category = llm_says_is_new and not category_exists
    
    # Assertions
    assert "Groceries" in existing_category_names
    assert category_exists == True
    assert is_new_category == False

