# 📚 Solution Design Documentation

**Architecture**: Modular Monolith  
**Stack**: FastAPI + PostgreSQL + Redis + Next.js

---

## 📖 Quick Start

1. **[solution-design.md](./solution-design.md)** - Start here! High-level architecture, project structure, and key flows

---

## 🔧 Domain Designs (9 Modules)

Each domain is a self-contained module within the monolith with clear boundaries:

### Core Domains
1. **[auth-domain-design.md](./auth-domain-design.md)** - Users, persons, JWT, Google OAuth
2. **[transaction-domain-design.md](./transaction-domain-design.md)** - Import, dedupe, multi-bank parsers
3. **[category-domain-design.md](./category-domain-design.md)** - Rules engine, auto-categorization
4. **[chat-domain-design.md](./chat-domain-design.md)** - AI assistant with tool calling

### Reporting Domains
5. **[report-domain-design.md](./report-domain-design.md)** - PDF/Excel orchestrator
6. **[recurring-domain-design.md](./recurring-domain-design.md)** - Pattern detection (algo+LLM)
7. **[insights-domain-design.md](./insights-domain-design.md)** - Trends, anomalies (algo+LLM)

### Platform Domains
8. **[payment-domain-design.md](./payment-domain-design.md)** - Stripe subscriptions
9. **[notification-domain-design.md](./notification-domain-design.md)** - WebSocket notifications

---

## 📋 Requirements

- **[requirements.md](./requirements.md)** - Original requirements
- **[report-requirements.md](./report-requirements.md)** - Multi-person & reporting features

---

## 🏗️ Architecture

```
Single FastAPI Backend
├── domains/
│   ├── auth/           # Module 1
│   ├── transactions/   # Module 2
│   ├── categories/     # Module 3
│   ├── chat/           # Module 4
│   ├── reports/        # Module 5
│   ├── recurring/      # Module 6
│   ├── insights/       # Module 7
│   ├── payments/       # Module 8
│   └── notifications/  # Module 9
├── shared/             # Common utilities
└── main.py             # Single FastAPI app
```

**Benefits**:
- ✅ Simple deployment (one service)
- ✅ Fast development (direct function calls)
- ✅ Easy debugging (single process)
- ✅ Domain boundaries (future-proof for microservices)

---

## 🎯 Key Features

**Multi-Person Management**: Manage wife, friend, customer data separately  
**Freemium**: 1,000 free transactions, unlimited premium  
**Hybrid AI**: Algorithm + LLM for 97% cost savings  
**Multi-Bank**: ENBD, FAB, WIO parsers  
**Real-time**: WebSocket notifications for recategorization, reports

---

## 🛠️ Tech Stack

**Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic  
**AI**: OpenAI GPT-5.2, Pandas, NumPy, SciPy  
**Database**: PostgreSQL 15, Redis 7  
**Reports**: WeasyPrint, openpyxl  
**Payments**: Stripe  
**Frontend**: Next.js 14, React, TypeScript, TailwindCSS

---

## 📦 Deployment

```bash
# Development
docker-compose up        # PostgreSQL + Redis + MinIO
cd backend && uv sync && uvicorn app.main:app --reload
cd frontend && npm run dev

# Production
docker build -t enbd-backend .
docker run -p 8000:8000 enbd-backend
```

---

## 📈 Future: Microservices Migration

When needed, extract domains as services:
1. Extract **Reports** domain (CPU-heavy) → Separate service
2. Add API Gateway (Kong/Nginx)
3. Replace in-process events with RabbitMQ

Each domain is **already independent** → easy extraction.

---

**Status**: Ready for Implementation ✅  
**Last Updated**: 2025-01-03
