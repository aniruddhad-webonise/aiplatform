"""
API runner script.

This script sets up the database and starts the API server.
"""
import os
import uvicorn
import logging
import argparse

from setup_db import setup_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the API server."""
    parser = argparse.ArgumentParser(description="Run the AI Platform API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    # Ensure config directory exists
    os.makedirs("config/tenants", exist_ok=True)
    
    # Set up the database
    setup_database()
    
    # Start the API server
    logger.info(f"Starting API server at http://{args.host}:{args.port}")
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main() 