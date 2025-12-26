# ENBD Expense Analyzer

A modern web application for analyzing ENBD bank transaction exports with AI-powered categorization.

## Features

- 📊 **Interactive Dashboard**: Visualize expenses with stacked column charts
- 📁 **File Upload**: Upload ENBD Excel transaction files via web UI
- 🤖 **AI Categorization**: Automatic transaction categorization using GPT-4o
- 🔍 **Smart Filtering**: Filter by date range, category, account, and merchant
- 💾 **Deduplication**: Automatic detection and prevention of duplicate transactions
- 📈 **Reports**: Weekly and monthly expense breakdowns
- 🎯 **Category Management**: Manage and update category rules

## Architecture

### Backend (FastAPI + PostgreSQL)
- RESTful API with FastAPI
- PostgreSQL database with SQLAlchemy ORM
- Alembic for database migrations
- OpenAI GPT-4o for intelligent categorization
- Comprehensive test suite with Testcontainers

### Frontend (Coming Soon)
- Next.js 14 + React + TypeScript
- TailwindCSS + shadcn/ui components
- Recharts for data visualization
- Real-time updates and filtering

## Quick Start

### Prerequisites
- Docker Desktop (for Mac/Windows) or Docker Engine (for Linux)
- Python 3.11+ with `uv` package manager
- OpenAI API key (for AI categorization)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd enbd-expense-analyzer
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. **Start with Docker Compose**
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

### Development Setup

**Backend development:**
```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Run tests:**
```bash
cd backend
uv run pytest tests/ -v
```

## API Endpoints

### Upload
- `POST /api/upload` - Upload ENBD XLSX files

### Transactions
- `GET /api/transactions` - Get transactions with filtering
  - Query params: `start_date`, `end_date`, `categories`, `accounts`, `merchant`, `page`, `page_size`

### Charts
- `GET /api/chart/weekly` - Weekly aggregated data for charts
- `GET /api/chart/monthly` - Monthly aggregated data for charts

### Statistics
- `GET /api/stats/summary` - Summary statistics (income, expenses, net)

### Health
- `GET /health` - Health check endpoint

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/enbd_analyzer_db

# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o  # Options: gpt-4o, gpt-5.2
```

### Category Rules

Edit `config/categories.json` to customize categorization rules:

```json
{
  "categories": [
    {
      "name": "Groceries",
      "keywords": ["CARREFOUR", "SPINNEYS", "LULU"]
    },
    {
      "name": "Transportation",
      "keywords": ["UBER", "CAREEM", "RTA"]
    }
  ]
}
```

## Testing

The project includes comprehensive integration tests:

```bash
cd backend
uv run pytest tests/ -v --cov=app
```

Tests use Testcontainers to spin up real PostgreSQL instances, ensuring true integration testing.

**Test Coverage:**
- ✅ Database schema and migrations (M1: 8 tests)
- ✅ File upload and import (M2: 6 tests)
- ✅ Data transformation (M3: 5 tests)
- ✅ Rule-based categorization (M4: 4 tests)
- ✅ LLM categorization with caching (M5: 6 tests)
- ✅ Data API with filtering (M6: 8 tests)

**Total: 37 passing tests**

## Project Structure

```
enbd-expense-analyzer/
├── backend/                  # FastAPI backend
│   ├── alembic/             # Database migrations
│   ├── app/
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── database.py      # Database configuration
│   │   ├── main.py          # FastAPI application
│   │   ├── routers/         # API endpoints
│   │   │   ├── upload.py    # File upload endpoints
│   │   │   └── data.py      # Data query endpoints
│   │   └── services/        # Business logic
│   │       ├── import_service.py      # XLSX import
│   │       ├── transform_service.py   # Data transformation
│   │       ├── category_service.py    # Rule-based categorization
│   │       └── llm_service.py         # AI categorization
│   ├── tests/               # Test suite
│   └── Dockerfile           # Backend container
├── config/                  # Configuration files
│   ├── categories.json      # Category rules
│   └── llm_categories.json  # AI categorization cache
├── data/                    # Transaction data (gitignored)
│   └── archive/            # Archived uploaded files
├── docs/                    # Documentation
├── docker-compose.yml       # Docker orchestration
└── README.md
```

## Development Workflow

### Adding a New Category

1. Edit `config/categories.json`
2. Add keywords for the new category
3. Re-run categorization via API or restart backend

### Running Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head
```

### Debugging

Check logs:
```bash
docker-compose logs -f backend
docker-compose logs -f postgres
```

## Roadmap

- [x] Backend API with PostgreSQL
- [x] File upload and import
- [x] AI-powered categorization
- [x] Data filtering and aggregation
- [ ] Frontend web application
- [ ] Interactive charts and visualizations
- [ ] Category management UI
- [ ] Multi-user support

## License

MIT

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a PR:

```bash
cd backend
uv run pytest tests/ -v
```
