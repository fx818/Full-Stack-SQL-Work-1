from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from api.routes import router
from services.database import db_service
from core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("Starting SQL Agent API...")
    print(f"SQLite Database: {settings.SQLITE_DB_PATH}")
    print(f"Supabase Host: {settings.SUPABASE_HOST}")
    
    # Test database connections
    try:
        # Test Supabase connection
        if db_service.health_check():
            print("✅ Supabase connection successful")
        else:
            print("❌ Supabase connection failed")
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down SQL Agent API...")
    try:
        db_service.close()
        print("✅ Database connections closed")
    except Exception as e:
        print(f"Error closing database connections: {e}")

# Create FastAPI application
app = FastAPI(
    title="SQL Agent API with Memory",
    description="A FastAPI application that processes natural language questions into SQL queries with conversation memory stored in Supabase",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",    # Django default
        "http://127.0.0.1:8000",   # Django alternative
        "http://localhost:3000",   # React default
        "http://127.0.0.1:3000",   # React alternative
        "http://localhost:8080",   # Vue.js default
        "http://127.0.0.1:8080",   # Vue.js alternative
        "http://localhost:5000",   # Flask default
        "http://127.0.0.1:5000",
        "https://sqlagent-nine.vercel.app/",
        "*"                        # Allow all origins for development (remove for production)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Add a simple root endpoint for testing
@app.get("/")
async def root():
    return {
        "message": "SQL Agent API is running!",
        "status": "healthy",
        "docs_url": "/docs",
        "api_prefix": "/api/v1"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return HTTPException(status_code=500, detail=f"Internal server error: {str(exc)}")


if __name__ == "__main__":
    print(f"Starting server at http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
