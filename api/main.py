"""
Main API endpoints for the AI platform.

This module provides the FastAPI routes for interacting with the platform.
"""
import os
import logging
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from ..core.orchestrator.orchestrator import Orchestrator
from ..core.config.config_manager import ConfigManager
from ..core.factories.agent_factory import AgentFactory
from ..core.interfaces.agent_interface import AgentType
from ..services.agents.chat_agent import ChatAgent
from ..services.agents.sql_agent import SQLAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Platform API",
    description="API for the AI platform with orchestrated agents",
    version="0.1.0"
)

# Initialize configuration
config_manager = ConfigManager()

# Register agent implementations
AgentFactory.register(AgentType.CHAT, ChatAgent)
AgentFactory.register(AgentType.SQL, SQLAgent)

# Initialize orchestrator
orchestrator = Orchestrator(config_manager)


# Request and response models
class QueryRequest(BaseModel):
    """Model for a query request."""
    query: str = Field(..., description="The query to process")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")


class QueryResponse(BaseModel):
    """Model for a query response."""
    response: Any = Field(..., description="The response content")
    success: bool = Field(..., description="Whether the query was successful")
    error: Optional[str] = Field(None, description="Error message, if any")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Helper functions
def get_tenant_id(x_tenant_id: str = Header(None)) -> str:
    """
    Extract and validate the tenant ID from the request headers.
    
    Args:
        x_tenant_id: The tenant ID header
        
    Returns:
        The validated tenant ID
        
    Raises:
        HTTPException: If the tenant ID is missing or invalid
    """
    if not x_tenant_id:
        # Use default tenant for testing
        return "default"
    
    # In a real implementation, validate that the tenant exists
    if x_tenant_id not in config_manager.get_tenant_ids():
        raise HTTPException(status_code=400, detail=f"Unknown tenant: {x_tenant_id}")
    
    return x_tenant_id


# API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Platform API",
        "version": "0.1.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "tenants": config_manager.get_tenant_ids()
    }


@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Process a query through the orchestrator.
    
    Args:
        request: The query request
        tenant_id: The tenant ID
        
    Returns:
        The query response
    """
    try:
        logger.info(f"Processing query for tenant {tenant_id}: {request.query[:50]}...")
        
        # Process the query through the orchestrator
        result = await orchestrator.process_request(request.query, tenant_id)
        
        return {
            "response": result.get("content"),
            "success": result.get("success", False),
            "error": result.get("error"),
            "metadata": result.get("metadata")
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# Startup event
@app.on_event("startup")
async def startup_event():
    """Perform startup tasks."""
    logger.info("API starting up...")
    
    # Add any additional startup tasks here
    
    # For testing purposes, ensure the default tenant directory exists
    os.makedirs("config/tenants", exist_ok=True)
    
    # Create a default tenant configuration if none exists
    default_tenant_path = "config/tenants/default.json"
    if not os.path.exists(default_tenant_path):
        default_config = {
            "tenant_id": "default",
            "name": "Default Tenant",
            "agents": {
                "chat": {
                    "type": "chat",
                    "model": "gpt-4o",
                    "temperature": 0.2
                },
                "sql": {
                    "type": "sql",
                    "model": "gpt-4o",
                    "temperature": 0.0,
                    "additional_params": {
                        "mcp_server": {
                            "type": "sqlite",
                            "connection_details": {
                                "database": "example.db"
                            }
                        }
                    }
                }
            },
            "workflows": {},
            "routing_rules": [
                {
                    "pattern": "(?i).*sql.*|.*database.*|.*query.*|.*table.*",
                    "agent": "sql"
                },
                {
                    "pattern": ".*",
                    "agent": "chat"
                }
            ],
            "mcp_servers": {}
        }
        
        os.makedirs(os.path.dirname(default_tenant_path), exist_ok=True)
        with open(default_tenant_path, "w") as f:
            import json
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default tenant configuration at {default_tenant_path}")
    
    logger.info("API startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Perform shutdown tasks."""
    logger.info("API shutting down...")
    
    # Add any cleanup tasks here
    
    logger.info("API shutdown complete") 