"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from contextlib import asynccontextmanager

from app.routers import upload, data, categories
from app.database import SessionLocal
from app.models import Category


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event to ensure default categories exist."""
    # Startup
    db = SessionLocal()
    try:
        # Ensure "Other" category exists
        other_category = db.query(Category).filter(Category.name == "Other").first()
        if not other_category:
            other_category = Category(name="Other", keywords=[])
            db.add(other_category)
            db.commit()
            print("✅ Created 'Other' category")
        else:
            print("✅ 'Other' category already exists")
    finally:
        db.close()
    
    yield
    # Shutdown (nothing to do)


app = FastAPI(
    title="ENBD Expense Analyzer API",
    description="Backend API for ENBD expense tracking and analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(data.router)
app.include_router(categories.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "enbd-backend",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "ENBD Expense Analyzer API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

