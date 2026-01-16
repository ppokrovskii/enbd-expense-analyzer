"""Main FastAPI application entry point."""
import logging
import os
import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Configure logging for the application
def configure_logging():
    """Configure application-wide logging with best practices."""
    # Create formatter with timestamp, level, logger name, and message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Only add handler if none exist (avoid duplicate logs)
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    # Jobs logger - INFO level for progress tracking
    jobs_logger = logging.getLogger("jobs")
    jobs_logger.setLevel(logging.INFO)
    
    # LLM logger - INFO level for API call tracking
    llm_logger = logging.getLogger("llm")
    llm_logger.setLevel(logging.INFO)
    
    # PgQueuer logger
    pgqueuer_logger = logging.getLogger("pgqueuer")
    pgqueuer_logger.setLevel(logging.INFO)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

# Initialize logging on module load
configure_logging()

logger = logging.getLogger("main")

# Import domain routers
from app.domains.transactions import router as transactions_router
from app.domains.categories import router as categories_router
from app.domains.chat import router as chat_router
from app.domains.accounts import router as accounts_router
from app.domains.jobs import router as jobs_router
from app.domains.notifications import router as notifications_router
from app.domains.persons import router as persons_router
from app.domains.recurring import router as recurring_router
from app.domains.insights import router as insights_router
from app.domains.reports import router as reports_router

# Import shared database
from app.shared.database import get_db, engine, SessionLocal

# Import models for backward compatibility - these ensure tables are created
from app.domains.transactions.models import Transaction, UnparsedFile
from app.domains.categories.models import Category, Rule, LLMCache
from app.domains.chat.models import ChatSession, ChatMessage, ChatContext, TokenUsage
from app.domains.accounts.models import UserAccount
from app.domains.jobs.models import BackgroundJob
from app.domains.persons.models import Person
from app.domains.recurring.models import RecurringGroup, RecurringOccurrence
from app.domains.insights.models import Insight
from app.domains.reports.models import Report


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - runs startup and shutdown logic."""
    # Startup: Ensure default "Other" category exists
    db = SessionLocal()
    try:
        other_category = db.query(Category).filter(Category.name == "Other").first()
        if not other_category:
            other_category = Category(name="Other", user_id="default_user")
            db.add(other_category)
            db.commit()
    except Exception as e:
        logger.warning(f"Could not ensure 'Other' category exists: {e}")
    finally:
        db.close()
    
    # Initialize PgQueuer if enabled
    pgq = None
    worker_task = None
    use_pgqueuer = os.environ.get("USE_PGQUEUER", "true").lower() == "true"
    
    if use_pgqueuer:
        try:
            from app.domains.jobs.tasks import init_pgqueuer
            database_url = os.environ.get("DATABASE_URL", "")
            if database_url:
                pgq = await init_pgqueuer(database_url)
                logger.info("🚀 PgQueuer initialized successfully")
                
                # Start worker in background task
                worker_task = asyncio.create_task(pgq.run())
                logger.info("👷 PgQueuer worker started in background")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize PgQueuer (falling back to threading): {e}")
    
    yield  # Application is running
    
    # Shutdown: Stop PgQueuer worker
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        logger.info("🛑 PgQueuer worker stopped")


app = FastAPI(
    title="ENBD Expense Analyzer",
    description="API for analyzing bank transactions and expenses",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include domain routers
app.include_router(transactions_router)  # /api/upload, /api/transactions, /api/chart/*
app.include_router(categories_router)    # /api/categories/*, /api/rules/*
app.include_router(chat_router)          # /api/chat/*
app.include_router(accounts_router)      # /api/accounts/*
app.include_router(jobs_router)          # /api/jobs/*
app.include_router(notifications_router) # /ws
app.include_router(persons_router)       # /api/persons/*
app.include_router(recurring_router)     # /api/recurring/*
app.include_router(insights_router)      # /api/insights/*
app.include_router(reports_router)       # /api/reports/*


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "message": "ENBD Expense Analyzer API v2.0.0",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "domains": [
            "transactions",
            "categories",
            "chat",
            "accounts",
            "jobs",
            "notifications",
            "persons",
            "recurring",
            "insights",
            "reports"
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "enbd-backend",
        "version": "2.0.0"
    }
