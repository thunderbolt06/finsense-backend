# FinSense - Autonomous Financial Research Copilot

A minimal financial research assistant built with Django, FastAPI, and Gemini LLM.

## Setup

1. Install dependencies:
```bash
cd finsense

# Using uv (recommended):
uv pip install -e .

# Or using pip:
pip install -e .

# Or install from pyproject.toml:
pip install fastapi django google-genai psycopg[binary,pool] dj-database-url httpx aiohttp pydantic pydantic-settings uvicorn
```

2. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Update `.env` with your API keys:
- `GEMINI_API_KEY`: Get from https://ai.google.dev/
- `SERPAPI_API_KEY`: Get from https://serpapi.com/

4. Setup PostgreSQL database:
```bash
# Option 1: Create database as postgres user
psql -U postgres -c "CREATE DATABASE finsense;"

# Option 2: Or if you have a different PostgreSQL user configured, use that
# The database will be created automatically by Django migrations if your DB user has permissions
```

5. Run migrations:
```bash
# Activate virtual environment first if using one:
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
# OR if using uv:
# uv run python manage.py migrate

# Create migrations (if needed):
python manage.py makemigrations

# Apply migrations to create database tables:
python manage.py migrate
```

**Note**: If you see "relation does not exist" errors, it means migrations haven't been run. Make sure to run `python manage.py migrate` before starting the server.

6. Start the server:
```bash
# Make sure virtual environment is activated
uvicorn app_server:app --reload --port 8000

# Or using Python module:
python -m uvicorn app_server:app --reload --port 8000
```

## API Endpoints

- `GET /api/ping` - Health check
- `GET /api/db-test` - Test database connection
- `POST /api/query` - Chat endpoint with streaming responses. Returns `chat_id` in the final `done` event.
- `GET /api/traces` - Get all chat histories from all chats

## Architecture

- Django for ORM and database models
- FastAPI for API endpoints
- Gemini LLM for chat responses
- SerpAPI for web search
- Tool calling pattern (function calling) for web search

