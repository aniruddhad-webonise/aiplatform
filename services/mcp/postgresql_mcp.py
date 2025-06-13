"""
PostgreSQL MCP server implementation that manages its own server and PostgreSQL connection.
"""
import os
import logging
from typing import Dict, Any, List, Optional
import asyncpg
import re
import httpx
from aiplatform.core.interfaces.mcp_interface import BaseMCPServer, MCPConfig, MCPRequest, MCPResponse
from dotenv import load_dotenv
from aiplatform.services.text_to_sql.api import fix_table_and_column_names

logger = logging.getLogger(__name__)

class PostgreSQLMCPServer(BaseMCPServer):
    """PostgreSQL MCP server implementation that manages its own server and PostgreSQL connection."""
    
    def __init__(self, config: MCPConfig):
        """
        Initialize PostgreSQL MCP server.
        
        Args:
            config: Configuration for this MCP server instance
        """
        super().__init__(config)
        self.connection_details = config.connection_details
        self.additional_params = config.additional_params or {}
        self.pool = None
        
        # Load environment variables
        load_dotenv()
        
        # Get database URL and interpolate environment variables
        self.database_url = config.connection_details.get('database_url', '')
        if self.database_url.startswith('${') and self.database_url.endswith('}'):
            env_var = self.database_url[2:-1]
            self.database_url = os.getenv(env_var, '')
            if not self.database_url:
                raise ValueError(f"Environment variable {env_var} not found")
        
        self.schema = config.connection_details.get('schema', 'public')
        self.text_to_sql_url = os.getenv('TEXT_TO_SQL_SERVICE_URL', 'http://localhost:8000')
        logger.info(f"Initialized PostgreSQL MCP server with schema: {self.schema}")
        
        if not self.database_url:
            raise ValueError("database_url is required for PostgreSQL MCP server")
    
    def _validate_read_only_query(self, query: str) -> None:
        """
        Validate that the query is read-only (SELECT only).
        
        Args:
            query: SQL query to validate
            
        Raises:
            ValueError: If query is not read-only
        """
        # Remove comments and normalize whitespace
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)  # Remove single-line comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)  # Remove multi-line comments
        query = ' '.join(query.split())  # Normalize whitespace
        
        # Convert to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check if query starts with SELECT
        if not query_lower.strip().startswith('select'):
            raise ValueError("Only SELECT queries are allowed for read-only access")
        
        # Check for forbidden keywords
        forbidden_keywords = [
            'insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate',
            'grant', 'revoke', 'commit', 'rollback', 'savepoint'
        ]
        
        for keyword in forbidden_keywords:
            if f' {keyword} ' in f' {query_lower} ':
                raise ValueError(f"Query contains forbidden keyword: {keyword}")
    
    def _is_read_only_query(self, query: str) -> bool:
        """Check if the query is read-only.
        
        Args:
            query: SQL query to check
            
        Returns:
            bool: True if the query is read-only, False otherwise
        """
        # Convert to lowercase for case-insensitive matching
        query_lower = query.lower().strip()
        
        # Check if query starts with SELECT or WITH
        if not (query_lower.startswith('select') or query_lower.startswith('with')):
            return False
            
        # Check for any write operations
        write_keywords = [
            'insert', 'update', 'delete', 'drop', 'alter', 'create',
            'truncate', 'grant', 'revoke', 'commit', 'rollback'
        ]
        
        for keyword in write_keywords:
            if f" {keyword} " in f" {query_lower} ":
                return False
                
        return True
    
    async def initialize(self) -> bool:
        """Initialize the PostgreSQL connection."""
        try:
            self.pool = await asyncpg.create_pool(self.database_url)
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {str(e)}")
    
    async def close(self) -> None:
        """Close the PostgreSQL connection."""
        try:
            if hasattr(self, 'pool'):
                await self.pool.close()
        except Exception as e:
            raise ConnectionError(f"Failed to disconnect from PostgreSQL database: {str(e)}")
    
    async def query(self, request: MCPRequest) -> MCPResponse:
        """Execute a query against the PostgreSQL database."""
        try:
            query = request.query.strip()
            logger.info(f"Executing query: {query}")
            
            # Clean up the query by removing markdown code block markers if present
            if query.startswith('```sql'):
                query = query[6:]
            if query.startswith('```'):
                query = query[3:]
            if query.endswith('```'):
                query = query[:-3]
            query = query.strip()
            
            # Check if the query is a natural language question
            if not query.lower().startswith(('select', 'with')):
                # Get schema information from config
                schema = await self.get_schema()
                
                # Get mappings from schema config
                schema_config = self.additional_params.get('schema_config', {})
                if not schema_config:
                    raise ValueError("Schema configuration is required for natural language queries")
                
                table_mappings = schema_config.get('table_mappings', {})
                column_mappings = schema_config.get('column_mappings', {})
                metric_mappings = schema_config.get('metric_mappings', {})
                data_type_rules = schema_config.get('data_type_rules', {})
                
                # Call text-to-SQL service
                try:
                    logger.info(f"Calling text-to-SQL service at {self.text_to_sql_url}")
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{self.text_to_sql_url}/generate-sql",
                            json={
                                "question": query,
                                "schema": schema,
                                "db_type": "postgresql",
                                "table_mappings": table_mappings,
                                "column_mappings": column_mappings,
                                "metric_mappings": metric_mappings,
                                "data_type_rules": data_type_rules
                            },
                            timeout=30.0  # Add timeout
                        )
                        
                        # Log response details
                        logger.info(f"Text-to-SQL service response status: {response.status_code}")
                        logger.info(f"Text-to-SQL service response headers: {response.headers}")
                        
                        # Check for HTTP errors
                        response.raise_for_status()
                        
                        # Parse response
                        result = response.json()
                        logger.info(f"Text-to-SQL service response: {result}")
                        
                        if not result.get("query"):
                            raise ValueError("No SQL query found in text-to-SQL service response")
                            
                        query = result["query"]
                        
                        # Fix table and column names
                        if table_mappings and column_mappings:
                            query = fix_table_and_column_names(query, table_mappings, column_mappings)
                        
                        logger.info(f"Generated SQL query: {query}")
                except httpx.HTTPError as e:
                    error_msg = f"Error calling text-to-SQL service: {str(e)}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nResponse status: {e.response.status_code}"
                        error_msg += f"\nResponse headers: {e.response.headers}"
                        error_msg += f"\nResponse body: {e.response.text}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error calling text-to-SQL service: {str(e)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Execute the query
            try:
                async with self.pool.acquire() as conn:
                    # Set the search path to the specified schema
                    await conn.execute(f'SET search_path TO {self.schema}')
                    
                    # Execute the query
                    result = await conn.fetch(query)
                    logger.info(f"Query executed successfully. Rows returned: {len(result)}")
                    
                    return MCPResponse(
                        content=result,
                        success=True,
                        metadata={"query": query}
                    )
            except asyncpg.PostgresError as e:
                error_msg = f"Database error: {str(e)}"
                logger.error(error_msg)
                return MCPResponse(
                    content=None,
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            logger.error(error_msg)
            return MCPResponse(
                content=None,
                success=False,
                error=error_msg
            )
    
    async def get_schema(self) -> Dict[str, Any]:
        """Get database schema information from config instead of querying the database."""
        try:
            # Get schema config from additional parameters
            schema_config = self.additional_params.get('schema_config', {})
            if not schema_config:
                raise ValueError("Schema configuration is required")
            
            # Build schema information from config
            schema = {}
            
            # Add tables
            for table in schema_config.get('tables', []):
                schema[table] = []
                # Get column mappings for this table
                table_mappings = schema_config.get('column_mappings', {}).get(table, {})
                for natural_name, actual_name in table_mappings.items():
                    # Determine data type from data_type_rules
                    data_type = "text"  # default
                    for type_name, columns in schema_config.get('data_type_rules', {}).items():
                        if actual_name in columns:
                            data_type = type_name
                            break
                    
                    schema[table].append({
                        'column_name': actual_name,
                        'data_type': data_type,
                        'is_nullable': True  # We don't have this info in config
                    })
            
            return schema
            
        except Exception as e:
            logger.error(f"Error getting schema from config: {str(e)}")
            raise
    
    async def get_views(self) -> Dict[str, Any]:
        """
        Get the database views information directly from PostgreSQL.
        
        Returns:
            Dictionary containing views information
        """
        try:
            async with self.pool.acquire() as conn:
                # Set the search path to the specified schema
                await conn.execute(f'SET search_path TO {self.schema}')
                
                # Get view information
                views_query = """
                SELECT 
                    viewname,
                    definition
                FROM 
                    pg_views
                WHERE 
                    schemaname = $1;
                """
                views = await conn.fetch(views_query, self.schema)
                
                # Organize into a more useful structure
                view_info = {}
                for row in views:
                    view_info[row['viewname']] = {
                        'definition': row['definition']
                    }
                
                return view_info
        except Exception as e:
            raise Exception(f"Failed to get views: {str(e)}") 