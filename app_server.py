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
# For development, allow common frontend ports
# Set CORS_ALLOW_ALL_ORIGINS=true in environment to allow all origins (development only)
ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() == "true"  # Default to true for development

if ALLOW_ALL_ORIGINS:
    # Development mode: Allow all origins using regex
    cors_config = {
        "allow_origin_regex": r".*",  # Allow all origins via regex
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "max_age": 3600,
    }
else:
    # Production mode: Explicit origins
    cors_config = {
        "allow_origins": [
            "http://localhost:1420",
            "http://localhost:3000",
            "http://localhost:5173",  # Vite default
            "http://localhost:5174",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://127.0.0.1:1420",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
            "http://0.0.0.0:1420",
            "http://0.0.0.0:3000",
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
            "Access-Control-Request-Method",
            "Access-Control-Request-Headers",
        ],
        "expose_headers": ["*"],
        "max_age": 3600,
    }

# Create FastAPI app
app = FastAPI(
    title="FinSense API",
    description="Financial research copilot API",
    lifespan=lifespan,
)

# Add CORS middleware - MUST be added before routes
middleware_kwargs = {
    "allow_credentials": cors_config["allow_credentials"],
    "allow_methods": cors_config["allow_methods"],
    "allow_headers": cors_config["allow_headers"],
    "expose_headers": cors_config["expose_headers"],
    "max_age": cors_config["max_age"],
}

if "allow_origin_regex" in cors_config:
    middleware_kwargs["allow_origin_regex"] = cors_config["allow_origin_regex"]
else:
    middleware_kwargs["allow_origins"] = cors_config["allow_origins"]

app.add_middleware(CORSMiddleware, **middleware_kwargs)


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
from routers.chat_router_structured import router as chat_router_structured
from routers.chat_router_messages import router as chat_router_messages
from routers.chat_router_agentic import router as chat_router_agentic
from features.files.files_router import router as files_router

app.include_router(chat_router)
app.include_router(chat_router_structured)
app.include_router(chat_router_messages)
app.include_router(chat_router_agentic)
app.include_router(files_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

