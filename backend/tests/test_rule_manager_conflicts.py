"""Integration tests for Rule Manager Conflict Detection API (Milestone 2)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.domains.categories.models import Category, Rule

client = TestClient(app)


class TestRuleConflictDetectionAPI:
    """Tests for POST /api/rules/check-conflicts endpoint."""
    
    def test_no_conflicts_for_unique_patterns(self, test_db):
        """No conflicts when keywords don't overlap with existing rules."""
        # Create a category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS", "COSTA"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        
        # Check for conflicts with different keywords
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["CARREFOUR", "LULU"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert data["conflicts"] == []
    
    def test_exact_duplicate_detection_error_severity(self, test_db):
        """Exact duplicate keywords should trigger error severity."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS", "COSTA"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        
        # Check for exact duplicate
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 1
        
        conflict = data["conflicts"][0]
        assert conflict["severity"] == "error"
        assert conflict["category_name"] == "Coffee"
        assert "STARBUCKS" in conflict["overlapping_keywords"]
    
    def test_partial_overlap_detection_warning_severity(self, test_db):
        """Partial keyword overlap should trigger warning severity."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS COFFEE"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        
        # Check for partial overlap (STARBUCKS is contained in STARBUCKS COFFEE)
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 1
        
        conflict = data["conflicts"][0]
        assert conflict["severity"] == "warning"  # Not exact match
        assert "STARBUCKS COFFEE" in conflict["overlapping_keywords"]
    
    def test_multiple_conflicts_detected(self, test_db):
        """Multiple conflicting rules should all be detected."""
        # Create categories and rules
        category1 = Category(user_id="test_user", name="Coffee", color="#FFC107")
        category2 = Category(user_id="test_user", name="Cafes", color="#FF5722")
        test_db.add_all([category1, category2])
        test_db.commit()
        test_db.refresh(category1)
        test_db.refresh(category2)
        
        rule1 = Rule(
            category_id=category1.id,
            user_id="test_user",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        rule2 = Rule(
            category_id=category2.id,
            user_id="test_user",
            keywords=["CAFE STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add_all([rule1, rule2])
        test_db.commit()
        
        # Check for conflicts
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 2
        
        category_names = [c["category_name"] for c in data["conflicts"]]
        assert "Coffee" in category_names
        assert "Cafes" in category_names
    
    def test_edit_mode_excludes_current_rule(self, test_db):
        """When editing, the current rule should be excluded from conflict check."""
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
        
        # Check conflicts excluding current rule (edit mode)
        response = client.post(
            "/api/rules/check-conflicts",
            json={
                "keywords": ["STARBUCKS"],
                "exclude_keywords": [],
                "rule_id": rule.id
            },
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False  # No conflict since we excluded the rule itself
    
    def test_empty_keywords_returns_no_conflicts(self, test_db):
        """Empty keywords should return no conflicts."""
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
        
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": [], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert data["conflicts"] == []
    
    def test_conflict_check_case_insensitive(self, test_db):
        """Conflict detection should be case insensitive."""
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
        
        # Check with lowercase
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["starbucks"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert data["conflicts"][0]["severity"] == "error"
    
    def test_conflict_check_or_patterns(self, test_db):
        """OR patterns (pipe-separated) should be checked correctly."""
        # Create category and rule with OR pattern
        category = Category(user_id="test_user", name="Coffee", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS|COSTA|TIM HORTONS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add(rule)
        test_db.commit()
        
        # Check for conflict with one of the alternatives
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["COSTA"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert data["conflicts"][0]["severity"] == "error"
    
    def test_user_isolation_in_conflict_check(self, test_db):
        """Conflict check should only consider rules for current user."""
        # Create categories and rules for two users
        category1 = Category(user_id="user1", name="Coffee1", color="#FFC107")
        category2 = Category(user_id="user2", name="Coffee2", color="#FF5722")
        test_db.add_all([category1, category2])
        test_db.commit()
        test_db.refresh(category1)
        test_db.refresh(category2)
        
        rule1 = Rule(
            category_id=category1.id,
            user_id="user1",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        rule2 = Rule(
            category_id=category2.id,
            user_id="user2",
            keywords=["STARBUCKS"],
            exclude_keywords=[],
            priority=0
        )
        test_db.add_all([rule1, rule2])
        test_db.commit()
        
        # User1 checks - should see their own rule conflict
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "user1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["category_name"] == "Coffee1"
        
        # User3 (new user) should see no conflicts
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "user3"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
    
    def test_conflict_response_includes_rule_details(self, test_db):
        """Conflict response should include all rule details."""
        # Create category and rule
        category = Category(user_id="test_user", name="Coffee Shop", color="#FFC107")
        test_db.add(category)
        test_db.commit()
        test_db.refresh(category)
        
        rule = Rule(
            category_id=category.id,
            user_id="test_user",
            keywords=["STARBUCKS", "COSTA", "DUNKIN"],
            exclude_keywords=["REFUND"],
            priority=10
        )
        test_db.add(rule)
        test_db.commit()
        test_db.refresh(rule)
        
        response = client.post(
            "/api/rules/check-conflicts",
            json={"keywords": ["STARBUCKS"], "exclude_keywords": []},
            headers={"X-User-Id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        
        conflict = data["conflicts"][0]
        assert conflict["rule_id"] == rule.id
        assert conflict["category_id"] == category.id
        assert conflict["category_name"] == "Coffee Shop"
        assert conflict["keywords"] == ["STARBUCKS", "COSTA", "DUNKIN"]
        assert "STARBUCKS" in conflict["overlapping_keywords"]

