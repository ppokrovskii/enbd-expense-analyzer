"""
Test Category Validation Logic (Unit Tests)
Tests the logic that determines if a category is new or existing
"""
import pytest


def validate_category_suggestion(suggested_category: str, llm_is_new: bool, existing_categories: list[str]) -> dict:
    """
    Simulates the frontend logic for validating if a suggested category is truly new.
    This is the logic that runs in frontend/app/categories/ai-suggestions/page.tsx
    
    Args:
        suggested_category: Category name suggested by LLM
        llm_is_new: Whether LLM thinks this is a new category  
        existing_categories: List of category names that exist in the database
        
    Returns:
        dict with validation results
    """
    category_exists = suggested_category in existing_categories
    is_new_category = llm_is_new and not category_exists
    create_new_category = is_new_category
    
    return {
        "suggested_category": suggested_category,
        "llm_is_new": llm_is_new,
        "category_exists": category_exists,
        "is_new_category": is_new_category,
        "create_new_category": create_new_category
    }


class TestCategoryValidationLogic:
    """Test the category validation logic that frontend uses"""
    
    def test_existing_category_suggested_by_llm(self):
        """
        When LLM suggests an EXISTING category (is_new_category=False),
        and it exists in the database,
        then is_new_category should be False
        """
        existing_categories = ["Groceries", "Shopping", "Dining & Restaurants", "Other"]
        
        result = validate_category_suggestion(
            suggested_category="Groceries",
            llm_is_new=False,
            existing_categories=existing_categories
        )
        
        assert result["category_exists"] == True
        assert result["is_new_category"] == False
        assert result["create_new_category"] == False
    
    def test_new_category_suggested_by_llm_not_in_db(self):
        """
        When LLM suggests a NEW category (is_new_category=True),
        and it does NOT exist in the database,
        then is_new_category should be True
        """
        existing_categories = ["Groceries", "Shopping", "Dining & Restaurants", "Other"]
        
        result = validate_category_suggestion(
            suggested_category="Personal Care & Beauty",
            llm_is_new=True,
            existing_categories=existing_categories
        )
        
        assert result["category_exists"] == False
        assert result["is_new_category"] == True
        assert result["create_new_category"] == True
    
    def test_llm_says_new_but_category_actually_exists(self):
        """
        BUG SCENARIO: When LLM suggests a category and marks it as new (is_new_category=True),
        but the category ACTUALLY EXISTS in the database,
        then frontend validation should override and set is_new_category=False
        
        This is the bug we're fixing - the frontend should detect that the category
        already exists and NOT show the "NEW CATEGORY" badge.
        """
        existing_categories = ["Groceries", "Shopping", "Personal Care & Beauty", "Other"]
        
        result = validate_category_suggestion(
            suggested_category="Personal Care & Beauty",
            llm_is_new=True,  # LLM incorrectly thinks this is new
            existing_categories=existing_categories  # But it exists!
        )
        
        # Frontend should detect that category exists
        assert result["category_exists"] == True
        # Override LLM's incorrect suggestion
        assert result["is_new_category"] == False
        assert result["create_new_category"] == False
    
    def test_case_sensitivity_matters(self):
        """
        Test that category matching is case-sensitive
        "Personal Care & Beauty" != "personal care & beauty"
        """
        existing_categories = ["Groceries", "personal care & beauty", "Other"]
        
        result = validate_category_suggestion(
            suggested_category="Personal Care & Beauty",  # Different case
            llm_is_new=True,
            existing_categories=existing_categories
        )
        
        # Should NOT match due to case difference
        assert result["category_exists"] == False
        assert result["is_new_category"] == True


if __name__ == "__main__":
    # Run quick manual test
    print("Testing category validation logic...\n")
    
    # Test 1: Existing category
    print("Test 1: Existing category")
    result1 = validate_category_suggestion("Groceries", False, ["Groceries", "Shopping", "Other"])
    print(f"  Result: is_new_category={result1['is_new_category']} (expected: False)")
    assert result1['is_new_category'] == False
    print("  ✓ PASS\n")
    
    # Test 2: New category
    print("Test 2: New category that doesn't exist")
    result2 = validate_category_suggestion("Personal Care & Beauty", True, ["Groceries", "Shopping", "Other"])
    print(f"  Result: is_new_category={result2['is_new_category']} (expected: True)")
    assert result2['is_new_category'] == True
    print("  ✓ PASS\n")
    
    # Test 3: BUG - LLM says new but exists
    print("Test 3: BUG - LLM says new but category already exists")
    result3 = validate_category_suggestion("Personal Care & Beauty", True, ["Groceries", "Personal Care & Beauty", "Other"])
    print(f"  Result: is_new_category={result3['is_new_category']} (expected: False)")
    print(f"  category_exists={result3['category_exists']} (expected: True)")
    assert result3['category_exists'] == True
    assert result3['is_new_category'] == False
    print("  ✓ PASS\n")
    
    print("All tests passed! ✓")

