"""
FastAPI application for FinSense.
Simplified version with no Redis, no telemetry.
"""
import os
from contextlib import asynccontextmanager
import uvicorn

# Setup Django BEFORE importing any Django models
import django
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsense.settings")
django.setup()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import connection_pool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Handle startup and shutdown events for the application"""
    # Initialize the database connection pool on application startup
    _ = await connection_pool.get_pool()
    
    # Yield control back to FastAPI
    yield
    
    # Close the database connection pool on application shutdown
    await connection_pool.close_pool()


# CORS configuration
cors_config = {
    "allow_origins": [
        "http://localhost:1420",
        "http://localhost:3000",
        "http://127.0.0.1:1420",
        "http://127.0.0.1:3000",
    ],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# Create FastAPI app
app = FastAPI(
    title="FinSense API",
    description="Financial research copilot API",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
)


@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/ping")
async def api_ping():
    """API health check endpoint."""
    return {"status": "ok", "message": "FinSense API is running"}


@app.get("/api/db-test")
async def db_test():
    """Test database connection by creating and reading a ChatWithContext record."""
    from db.models import ChatWithContext
    
    try:
        # Create a test chat using sync method (Django ORM in async context)
        import asyncio
        loop = asyncio.get_event_loop()
        test_chat = await loop.run_in_executor(
            None,
            lambda: ChatWithContext.objects.create(
                title="Test Chat",
                chat_history="[]",
                finished=False,
            )
        )
        
        # Read it back
        retrieved = await loop.run_in_executor(
            None,
            lambda: ChatWithContext.objects.get(id=test_chat.id)
        )
        
        return {
            "status": "ok",
            "created_id": str(test_chat.id),
            "retrieved_id": str(retrieved.id),
            "title": retrieved.title,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "hint": "Make sure you have run: python manage.py migrate"
        }


# Include routers AFTER Django setup
# Import at the end to ensure Django is configured
from routers.chat_router import router as chat_router

app.include_router(chat_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

