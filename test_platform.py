"""
Test script for the AI platform.

This script tests the core functionality of the platform, including:
1. Chat agent responses
2. SQL agent queries
3. Database connectivity
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

# Add the parent directory to Python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiplatform.core.config.config_manager import ConfigManager
from aiplatform.core.orchestrator.orchestrator import Orchestrator
from aiplatform.core.factories.agent_factory import AgentFactory
from aiplatform.core.factories.mcp_factory import MCPFactory
from aiplatform.core.interfaces.agent_interface import AgentType
from aiplatform.services.agents.chat_agent import ChatAgent
from aiplatform.services.agents.sql_agent import SQLAgent
from aiplatform.services.mcp.sqlite_mcp import SQLiteMCPServer
from aiplatform.setup_db import setup_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_chat_agent(orchestrator: Orchestrator, tenant_id: str):
    """Test the chat agent with various queries."""
    logger.info("\n=== Testing Chat Agent ===")
    
    test_queries = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms",
        "What are the three laws of robotics?"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: {query}")
        response = await orchestrator.process_request(query, tenant_id)
        logger.info(f"Response: {response.get('content')}")
        logger.info(f"Success: {response.get('success')}")
        if response.get('error'):
            logger.error(f"Error: {response.get('error')}")

async def test_sql_agent(orchestrator: Orchestrator, tenant_id: str):
    """Test the SQL agent with various database queries."""
    logger.info("\n=== Testing SQL Agent ===")
    
    test_queries = [
        "Show me all users in the database",
        "What electronics products do we have?",
        "List all orders with their total amounts",
        "Find products that cost less than $100"
    ]
    
    for query in test_queries:
        logger.info(f"\nQuery: {query}")
        response = await orchestrator.process_request(query, tenant_id)
        logger.info(f"Response: {response.get('content')}")
        logger.info(f"Success: {response.get('success')}")
        if response.get('error'):
            logger.error(f"Error: {response.get('error')}")

async def main():
    """Run the tests."""
    try:
        # Ensure database is set up
        setup_database()
        
        # Initialize configuration
        config_manager = ConfigManager()
        
        # Register agent implementations
        AgentFactory.register(AgentType.CHAT, ChatAgent)
        AgentFactory.register(AgentType.SQL, SQLAgent)
        
        # Register MCP server implementations
        MCPFactory.register("sqlite", SQLiteMCPServer)
        
        # Initialize orchestrator
        orchestrator = Orchestrator(config_manager)
        
        # Test with default tenant
        tenant_id = "default"
        
        # Run tests
        await test_chat_agent(orchestrator, tenant_id)
        await test_sql_agent(orchestrator, tenant_id)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 