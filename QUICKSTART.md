# Quick Start Guide

## Getting Started in 5 Minutes

### 1. Prerequisites

Ensure you have:
- ✅ Docker Desktop running
- ✅ An OpenAI API key (from https://platform.openai.com/api-keys)

### 2. Setup Environment

```bash
# Clone and enter the project
cd enbd-expense-analyzer

# Create environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Start the Application

```bash
# Start all services (PostgreSQL + Backend API)
docker-compose up -d

# Check status
docker-compose ps
```

The API will be running at **http://localhost:8000**

### 4. Verify It's Working

```bash
# Health check
curl http://localhost:8000/health

# Expected response: {"status":"healthy","service":"enbd-backend","version":"1.0.0"}
```

### 5. Upload Your First File

Using the API docs (Swagger UI):
1. Open http://localhost:8000/docs in your browser
2. Navigate to `POST /api/upload`
3. Click "Try it out"
4. Upload your ENBD Excel file
5. Click "Execute"

Or use curl:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@/path/to/your/ENBD_Statement.xlsx"
```

### 6. View Your Data

**Get transactions:**
```bash
curl "http://localhost:8000/api/transactions?page=1&page_size=10"
```

**Get summary stats:**
```bash
curl "http://localhost:8000/api/stats/summary"
```

**Get weekly chart data:**
```bash
curl "http://localhost:8000/api/chart/weekly"
```

## Common Commands

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f postgres
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### Run Database Migrations
```bash
docker-compose exec backend alembic upgrade head
```

### Access Database
```bash
docker-compose exec postgres psql -U user -d enbd_analyzer_db
```

## Troubleshooting

### Port 8000 Already in Use
```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 on host instead
```

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres
```

### Clear All Data and Start Fresh
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d    # Start fresh
```

## Next Steps

1. **Customize Categories**: Edit `config/categories.json` to add your own categorization rules
2. **Review API Docs**: Visit http://localhost:8000/docs for full API documentation
3. **Run Tests**: `cd backend && uv run pytest tests/ -v`
4. **Monitor Performance**: Check logs and database for any issues

## API Endpoints Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/upload` | POST | Upload ENBD files |
| `/api/transactions` | GET | Get transactions (with filters) |
| `/api/chart/weekly` | GET | Weekly aggregated data |
| `/api/chart/monthly` | GET | Monthly aggregated data |
| `/api/stats/summary` | GET | Summary statistics |

## Getting Help

- Check the logs: `docker-compose logs -f`
- Read the full README.md for detailed documentation
- Review test examples in `backend/tests/`

