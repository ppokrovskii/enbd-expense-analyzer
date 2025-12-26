"""Seed categories from config/categories.json into the database."""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Category
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://enbd_user:enbd_password@localhost:5432/enbd_db")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Load categories from config
    config_path = Path(__file__).parent.parent / "config" / "categories.json"
    with open(config_path, 'r') as f:
        categories_data = json.load(f)
    
    # Clear existing categories
    print("🗑️  Clearing existing categories...")
    db.query(Category).delete()
    db.commit()
    
    # Add categories
    print(f"📝 Adding {len(categories_data)} categories...")
    for category_name, keywords in categories_data.items():
        category = Category(
            name=category_name,
            keywords=keywords
        )
        db.add(category)
        print(f"   ✅ {category_name}: {len(keywords)} keywords")
    
    db.commit()
    print(f"\n✨ Successfully seeded {len(categories_data)} categories!")
    
except Exception as e:
    print(f"❌ Error seeding categories: {e}")
    db.rollback()
finally:
    db.close()

