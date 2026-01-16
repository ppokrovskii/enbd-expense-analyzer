"""Integration tests for Rule Manager Editing API (Milestone 3)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.domains.categories.models import Category, Rule

client = TestClient(app)


class TestRuleEditingAPI:
    """Tests for rule editing via PUT /api/rules/{id} endpoint."""
    
    def test_update_rule_keywords(self, test_db):
        """Update rule keywords via PUT endpoint."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        # Update keywords
        response = client.put(
            f"/api/rules/{rule.id}",
            json={"keywords": ["STARBUCKS", "COSTA", "TIM HORTONS"]},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == ["STARBUCKS", "COSTA", "TIM HORTONS"]
        assert data["exclude_keywords"] == []  # Unchanged
    
    def test_update_rule_exclude_keywords(self, test_db):
        """Update rule exclude_keywords via PUT endpoint."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        # Update exclude_keywords
        response = client.put(
            f"/api/rules/{rule.id}",
            json={"exclude_keywords": ["REFUND", "REVERSAL"]},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == ["STARBUCKS"]  # Unchanged
        assert data["exclude_keywords"] == ["REFUND", "REVERSAL"]
    
    def test_update_rule_priority(self, test_db):
        """Update rule priority via PUT endpoint."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        # Update priority
        response = client.put(
            f"/api/rules/{rule.id}",
            json={"priority": 10},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 10
    
    def test_update_multiple_fields(self, test_db):
        """Update multiple rule fields at once."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["OLD"],
            exclude_keywords=["OLD_EXCLUDE"],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        # Update all fields
        response = client.put(
            f"/api/rules/{rule.id}",
            json={
                "keywords": ["NEW1", "NEW2"],
                "exclude_keywords": ["NEW_EXCLUDE"],
                "priority": 50
            },
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["keywords"] == ["NEW1", "NEW2"]
        assert data["exclude_keywords"] == ["NEW_EXCLUDE"]
        assert data["priority"] == 50
    
    def test_update_rule_not_found(self, test_db):
        """Attempting to update non-existent rule returns 404."""
        response = client.put(
            "/api/rules/99999",
            json={"keywords": ["TEST"]},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_rule_user_isolation(self, test_db):
        """Users can only update their own rules."""
        # Create category and rule for user1
        category = Category(user_id="user1", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="user1",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        # User2 tries to update user1's rule
        response = client.put(
            f"/api/rules/{rule.id}",
            json={"keywords": ["HACKED"]},
            headers={"X-User-Id": "user2"}
        )
        
        assert response.status_code == 404  # Should not be found for user2
    
    def test_delete_rule(self, test_db):
        """Delete rule via DELETE endpoint."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        rule_id = rule.id
        
        # Delete the rule
        response = client.delete(
            f"/api/rules/{rule_id}",
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 204
        
        # Verify rule is deleted
        deleted_rule = test_db.query(Rule).filter(Rule.id == rule_id).first()
        assert deleted_rule is None
    
    def test_delete_rule_not_found(self, test_db):
        """Attempting to delete non-existent rule returns 404."""
        response = client.delete(
            "/api/rules/99999",
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 404
    
    def test_create_rule(self, test_db):
        """Create new rule via POST endpoint."""
        # Create category
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        # Create rule
        response = client.post(
            "/api/rules/",
            json={
                "category_id": category.id,
                "keywords": ["STARBUCKS", "COSTA"],
                "exclude_keywords": ["REFUND"],
                "priority": 5
            },
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 201
        data = response.json()
        # Response is now nested: { rule: {...}, job_id: "...", ... }
        rule_data = data["rule"]
        assert rule_data["category_id"] == category.id
        assert rule_data["keywords"] == ["STARBUCKS", "COSTA"]
        assert rule_data["exclude_keywords"] == ["REFUND"]
        assert rule_data["priority"] == 5
    
    def test_create_rule_invalid_category(self, test_db):
        """Creating rule with invalid category_id returns 404."""
        response = client.post(
            "/api/rules/",
            json={
                "category_id": 99999,
                "keywords": ["TEST"],
                "exclude_keywords": [],
                "priority": 0
            },
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 404
        assert "category" in response.json()["detail"].lower()
    
    def test_list_rules_with_pagination(self, test_db):
        """List rules with pagination via GET endpoint."""
        # Create category
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        # Create multiple rules
        for i in range(5):
            rule = Rule(
                category_id=category.id,
                user_id="test_user",
                keywords=[f"KEYWORD_{i}"],
                exclude_keywords=[],
                priority=i
            )
            test_db.add(rule)
        test_db.commit()
        
        # Get first page
        response = client.get(
            "/api/rules/?offset=0&limit=3",
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["has_more"] is True
        
        # Get second page
        response = client.get(
            "/api/rules/?offset=3&limit=3",
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["has_more"] is False
    
    def test_list_rules_includes_category_name(self, test_db):
        """List rules includes category_name in response."""
        # Create category
        category = Category(user_id="test_user", name="Coffee Shop", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        # Create rule
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        
        response = client.get(
            "/api/rules/",
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category_name"] == "Coffee Shop"

