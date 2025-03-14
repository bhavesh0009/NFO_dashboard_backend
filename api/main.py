"""
Main FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

# Create FastAPI application
app = FastAPI(
    title="Market Data API",
    description="API for accessing market data from Angel One",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include the router
app.include_router(router)

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "status": "ok",
        "message": "Market Data API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 