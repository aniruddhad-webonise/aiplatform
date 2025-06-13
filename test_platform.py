"""
Test script for the AI platform.

This script tests the core functionality of the platform, including:
1. Chat agent responses
2. SQL agent queries
3. Database connectivity
4. Multi-tenant support
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
from aiplatform.core.interfaces.mcp_interface import MCPConfig
from aiplatform.services.agents.chat_agent import ChatAgent
from aiplatform.services.agents.sql_agent import SQLAgent
from aiplatform.services.mcp.sqlite_mcp import SQLiteMCPServer
from aiplatform.services.mcp.postgresql_mcp import PostgreSQLMCPServer
from aiplatform.setup_db import setup_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_postgresql_mcp_server():
    """Test the PostgreSQL MCP server with various queries."""
    logger.info("\n=== Testing PostgreSQL MCP Server ===")
    
    # Initialize configuration
    config_manager = ConfigManager()
    tenant_config = config_manager.get_tenant_config("zcg_affinity_g")
    assert tenant_config, "Tenant config for zcg_affinity_g not found"
    
    # Get SQL agent config and its additional params
    sql_agent_config = tenant_config.agents["sql"]
    additional_params = sql_agent_config.get("additional_params", {})
    
    # Get MCP server config and schema config from additional params
    mcp_server_config = additional_params.get("mcp_server", {})
    schema_config = additional_params.get("schema_config", {})
    
    if not schema_config:
        raise ValueError("Schema configuration is required in SQL agent additional_params")
    
    mcp_type = mcp_server_config["type"]
    connection_details = mcp_server_config["connection_details"]
    
    # Create MCP config with schema_config in additional_params
    mcp_config = MCPConfig(
        mcp_type=mcp_type,
        connection_details=connection_details,
        additional_params={"schema_config": schema_config}  # Pass schema_config as a nested parameter
    )
    
    # Debug: Print connection details
    logger.info(f"\nConnection Details:")
    logger.info(f"MCP Type: {mcp_type}")
    logger.info(f"Database URL: {connection_details.get('database_url')}")
    logger.info(f"Schema: {connection_details.get('schema')}")
    logger.info(f"Full Connection Details: {connection_details}")
    logger.info(f"Schema Config: {schema_config}")
    
    mcp_server = await MCPFactory.create(mcp_config)
    
    try:
        # Connect to the server
        logger.info("\nAttempting to connect to PostgreSQL MCP server...")
        await mcp_server.initialize()
        logger.info("Successfully connected to PostgreSQL MCP server")
        
        # Test valid SELECT queries
        valid_queries = [
            "SELECT * FROM affinity_gaming.affinity_gaming_balance_sheet limit 5"
        ]
        
        for query in valid_queries:
            logger.info(f"\nTesting valid query: {query}")
            try:
                from aiplatform.core.interfaces.mcp_interface import MCPRequest
                mcp_request = MCPRequest(query=query, tenant_id="zcg_affinity_g")
                results = await mcp_server.query(mcp_request)
                logger.info(f"Query executed successfully. Results: {results.content}")
            except Exception as e:
                logger.error(f"Valid query failed: {str(e)}")
        
        """
        # Test invalid queries (should be rejected)
        invalid_queries = [
            "INSERT INTO balance_sheet (date, amount) VALUES ('2024-01-01', 1000)",
            "UPDATE financial_data SET amount = 2000 WHERE id = 1",
            "DELETE FROM transactions WHERE date < '2023-01-01'",
            "DROP TABLE balance_sheet",
            "ALTER TABLE financial_data ADD COLUMN new_column INT",
            "CREATE TABLE new_table (id INT)",
            "TRUNCATE TABLE transactions",
            "GRANT SELECT ON financial_data TO user1",
            "COMMIT",
            "SELECT * FROM balance_sheet; DROP TABLE balance_sheet"  # SQL injection attempt
        ]
        
        for query in invalid_queries:
            logger.info(f"\nTesting invalid query: {query}")
            try:
                from aiplatform.core.interfaces.mcp_interface import MCPRequest
                mcp_request = MCPRequest(query=query, tenant_id="zcg_affinity_g")
                result = await mcp_server.query(mcp_request)
                if result.success:
                    logger.error("Invalid query was not rejected!")
                else:
                    logger.info(f"Query correctly rejected: {result.error}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
        
        
        # Test schema and views
        logger.info("\nTesting schema retrieval")
        schema = await mcp_server.get_schema()
        logger.info(f"Schema: {schema}")
        
        logger.info("\nTesting views retrieval")
        views = await mcp_server.get_views()
        logger.info(f"Views: {views}")
        """
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        # Disconnect from the server
        await mcp_server.close()
        logger.info("Disconnected from PostgreSQL MCP server")

async def test_chat_agent(orchestrator: Orchestrator, tenant_id: str):
    """Test the chat agent with various queries."""
    logger.info(f"\n=== Testing Chat Agent for tenant: {tenant_id} ===")
    
    test_queries = {
        "default": [
            "What is the capital of France?",
            "Explain quantum computing in simple terms",
            "What are the three laws of robotics?"
        ],
        "zcg_affinity_g": [
            "Explain what a balance sheet is",
            "What is the difference between revenue and profit?",
            "How do you calculate working capital?"
        ]
    }
    
    for query in test_queries[tenant_id]:
        logger.info(f"\nQuery: {query}")
        response = await orchestrator.process_request(query, tenant_id)
        logger.info(f"Response: {response.get('content')}")
        logger.info(f"Success: {response.get('success')}")
        if response.get('error'):
            logger.error(f"Error: {response.get('error')}")

async def test_sql_agent(orchestrator: Orchestrator, tenant_id: str):
    """Test the SQL agent with various database queries."""
    logger.info(f"\n=== Testing SQL Agent for tenant: {tenant_id} ===")
    
    # Get tenant config to access schema_prefix
    config_manager = ConfigManager()
    tenant_config = config_manager.get_tenant_config(tenant_id)
    schema_prefix = tenant_config.agents["sql"]["additional_params"]["schema_config"].get("schema_prefix", "affinity_gaming")
    logger.info(f"Using schema prefix: {schema_prefix}")
    
    test_queries = {
        "default": [
            "Show me all users in the database",
            "What electronics products do we have?",
            "List all orders with their total amounts",
            "Find products that cost less than $100"
        ],
        "zcg_affinity_g": [
            "Find the total ending balance for Gross Profit metric in profit and loss table for January for year 2025",
            "What is the mtd value for entity SILVER SEVENS CASINO and gl number 11500 for month 1 and month 2 in cash flow for year 2025"
        ]
    }
    
    for query in test_queries[tenant_id]:
        logger.info(f"\nQuery: {query}")
        # Add schema_prefix to the request
        response = await orchestrator.process_request(
            query, 
            tenant_id,
            additional_params={"schema_prefix": schema_prefix}
        )
        logger.info(f"Response: {response.get('content')}")
        logger.info(f"Success: {response.get('success')}")
        if response.get('error'):
            logger.error(f"Error: {response.get('error')}")

async def test_tenant(tenant_id: str):
    """Test a specific tenant."""
    logger.info(f"\n{'='*50}")
    logger.info(f"Testing tenant: {tenant_id}")
    logger.info(f"{'='*50}")
    
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        
        # Register agent implementations
        AgentFactory.register(AgentType.CHAT, ChatAgent)
        AgentFactory.register(AgentType.SQL, SQLAgent)
        
        # Register MCP server implementations
        MCPFactory.register("sqlite", SQLiteMCPServer)
        MCPFactory.register("postgresql", PostgreSQLMCPServer)
        
        # Initialize orchestrator
        orchestrator = Orchestrator(config_manager)
        
        # Run tests
        #await test_chat_agent(orchestrator, tenant_id)
        await test_sql_agent(orchestrator, tenant_id)
        
    except Exception as e:
        logger.error(f"Test failed for tenant {tenant_id}: {e}")
        raise

async def main():
    """Run the tests for all tenants."""
    try:
        # Ensure database is set up
        setup_database()
        
        # Test PostgreSQL MCP server
        #await test_postgresql_mcp_server()
        
        # Test each tenant
        #tenants = ["default", "zcg_affinity_g"]
        tenants = ["zcg_affinity_g"]
        for tenant_id in tenants:
            await test_tenant(tenant_id)
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 