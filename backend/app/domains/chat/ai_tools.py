"""AI Tool Handlers for OpenAI Function Calling."""
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.domains.transactions.service import TransactionService


class AITools:
    """Collection of AI tool handlers for chat assistant."""
    
    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for all available tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_transactions",
                    "description": "Query and analyze transaction data with various filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "categories": {"type": "array", "items": {"type": "string"}},
                            "accounts": {"type": "array", "items": {"type": "string"}},
                            "merchant": {"type": "string"},
                            "exclude_transfers": {"type": "boolean", "default": False}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_spending_trends",
                    "description": "Get spending trends over time with weekly or monthly aggregation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "grouping": {"type": "string", "enum": ["weekly", "monthly"]},
                            "categories": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["start_date", "end_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_categories",
                    "description": "Get all available spending categories.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_category_details",
                    "description": "Get detailed information about a specific category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_name": {"type": "string", "description": "Name of the category"}
                        },
                        "required": ["category_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_category",
                    "description": "Create a new spending category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Category name"},
                            "color": {"type": "string", "description": "Hex color code (e.g. #FF6B6B)"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_category",
                    "description": "Update an existing category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_name": {"type": "string", "description": "Current category name"},
                            "new_name": {"type": "string", "description": "New name for the category"},
                            "new_color": {"type": "string", "description": "New hex color code"}
                        },
                        "required": ["category_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_category",
                    "description": "Delete a category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category_name": {"type": "string", "description": "Name of the category to delete"}
                        },
                        "required": ["category_name"]
                    }
                }
            }
        ]
    
    @staticmethod
    def execute_tool(
        tool_name: str,
        arguments: Dict[str, Any],
        db: Session,
        user_id: str
    ) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        handlers = {
            "query_transactions": AITools._handle_query_transactions,
            "get_spending_trends": AITools._handle_spending_trends,
            "list_categories": AITools._handle_list_categories,
            "get_category_details": AITools._handle_get_category_details,
            "create_category": AITools._handle_create_category,
            "update_category": AITools._handle_update_category,
            "delete_category": AITools._handle_delete_category,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        return handler(arguments, db, user_id)
    
    @staticmethod
    def _handle_query_transactions(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle query_transactions tool."""
        start_date = None
        end_date = None
        if "start_date" in arguments:
            start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d").date()
        if "end_date" in arguments:
            end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d").date()
        
        transactions, total = TransactionService.get_filtered_transactions(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            categories=arguments.get("categories"),
            accounts=arguments.get("accounts"),
            merchant=arguments.get("merchant"),
            exclude_transfers=arguments.get("exclude_transfers", False),
            page=1,
            page_size=100
        )
        
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
            "summary": {
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "net": round(total_income - total_expenses, 2),
                "transaction_count": total
            },
            "top_categories": top_categories
        }
    
    @staticmethod
    def _handle_spending_trends(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle get_spending_trends tool."""
        start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d").date()
        grouping = arguments.get("grouping", "monthly")
        
        if grouping == "weekly":
            raw_data = TransactionService.get_weekly_aggregation(
                db=db, user_id=user_id, start_date=start_date, end_date=end_date,
                categories=arguments.get("categories")
            )
        else:
            raw_data = TransactionService.get_monthly_aggregation(
                db=db, user_id=user_id, start_date=start_date, end_date=end_date,
                categories=arguments.get("categories")
            )
        
        serializable_data = []
        for row in raw_data:
            serializable_data.append({
                "period": row.period.isoformat() if hasattr(row.period, 'isoformat') else str(row.period),
                "category": row.category,
                "total": float(row.total) if row.total else 0.0
            })
        
        return {"grouping": grouping, "data": serializable_data}
    
    @staticmethod
    def _handle_list_categories(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle list_categories tool."""
        from app.domains.categories.models import Category
        from app.domains.transactions.models import Transaction
        
        categories = db.query(Category).filter(Category.user_id == user_id).all()
        
        # Get transaction counts and totals per category
        category_stats = db.query(
            Transaction.category,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount_signed).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.category.isnot(None)
        ).group_by(Transaction.category).all()
        
        stats_map = {row.category: {'count': row.count, 'total': float(row.total) if row.total else 0} for row in category_stats}
        
        return {
            "categories": [
                {
                    "name": cat.name,
                    "color": cat.color,
                    "transaction_count": stats_map.get(cat.name, {}).get('count', 0),
                    "total_amount": stats_map.get(cat.name, {}).get('total', 0)
                }
                for cat in categories
            ]
        }
    
    @staticmethod
    def _handle_get_category_details(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle get_category_details tool."""
        from app.domains.categories.models import Category
        from app.domains.transactions.models import Transaction
        
        category_name = arguments["category_name"]
        
        # Get category
        category = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == category_name
        ).first()
        
        if not category:
            raise ValueError(f"Category '{category_name}' not found")
        
        # Get stats for this category
        stats = db.query(
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount_signed).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.category == category_name
        ).first()
        
        return {
            "name": category.name,
            "color": category.color,
            "transaction_count": stats.count if stats else 0,
            "total_amount": float(stats.total) if stats and stats.total else 0
        }
    
    @staticmethod
    def _handle_create_category(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle create_category tool."""
        from app.domains.categories.models import Category
        
        name = arguments["name"]
        color = arguments.get("color", "#808080")  # Default gray
        
        # Check if category already exists
        existing = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Category '{name}' already exists")
        
        # Create category
        category = Category(
            user_id=user_id,
            name=name,
            color=color
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        
        return {
            "name": category.name,
            "color": category.color,
            "transaction_count": 0
        }
    
    @staticmethod
    def _handle_update_category(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle update_category tool."""
        from app.domains.categories.models import Category
        
        category_name = arguments["category_name"]
        
        # Get category
        category = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == category_name
        ).first()
        
        if not category:
            raise ValueError(f"Category '{category_name}' not found")
        
        # Update fields
        if "new_name" in arguments:
            category.name = arguments["new_name"]
        if "new_color" in arguments:
            category.color = arguments["new_color"]
        
        db.commit()
        db.refresh(category)
        
        return {
            "name": category.name,
            "color": category.color
        }
    
    @staticmethod
    def _handle_delete_category(arguments: Dict[str, Any], db: Session, user_id: str) -> Dict[str, Any]:
        """Handle delete_category tool."""
        from app.domains.categories.models import Category
        
        category_name = arguments["category_name"]
        
        # Get category
        category = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == category_name
        ).first()
        
        if not category:
            raise ValueError(f"Category '{category_name}' not found")
        
        # Delete category
        db.delete(category)
        db.commit()
        
        return {
            "deleted": True,
            "message": f"Category '{category_name}' has been deleted"
        }
