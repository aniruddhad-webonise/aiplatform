"""
SQLite MCP server implementation.

This module implements a Model Context Protocol (MCP) server for SQLite databases.
"""
import os
import sqlite3
import logging
from typing import Dict, Any, Optional, List

from ...core.interfaces.mcp_interface import BaseMCPServer, MCPConfig, MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class SQLiteMCPServer(BaseMCPServer):
    """
    MCP server for SQLite databases.
    """
    
    def __init__(self, config: MCPConfig):
        """
        Initialize the SQLite MCP server.
        
        Args:
            config: Configuration for the server
        """
        super().__init__(config)
        
        # Extract connection details
        self.database_path = config.connection_details.get("database", "example.db")
        
        # Connection will be initialized on demand
        self.connection = None
    
    async def initialize(self) -> bool:
        """
        Initialize the SQLite connection.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            # Ensure the database file exists or can be created
            db_dir = os.path.dirname(self.database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Test connection
            self.connection = sqlite3.connect(self.database_path)
            
            # Enable dictionary access to rows
            self.connection.row_factory = sqlite3.Row
            
            logger.info(f"Successfully connected to SQLite database at {self.database_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite connection: {e}")
            return False
    
    async def query(self, request: MCPRequest) -> MCPResponse:
        """
        Execute a query against the SQLite database.
        
        Args:
            request: The request to process
            
        Returns:
            An MCP response object
        """
        if not self.connection:
            try:
                await self.initialize()
            except Exception as e:
                return MCPResponse(
                    content=None,
                    success=False,
                    error=f"Failed to initialize database connection: {e}"
                )
        
        try:
            # Check if the query is a special command
            if request.query.strip().upper() == "SHOW SCHEMA":
                return await self._get_schema()
            
            # Execute the SQL query
            cursor = self.connection.cursor()
            cursor.execute(request.query)
            
            # Get the results
            if cursor.description:
                # SELECT query - return rows as list of dicts
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows]
            else:
                # Non-SELECT query - return affected row count
                self.connection.commit()
                result = {"rows_affected": cursor.rowcount}
            
            return MCPResponse(
                content=result,
                success=True,
                metadata={
                    "query": request.query
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return MCPResponse(
                content=None,
                success=False,
                error=f"Error executing query: {str(e)}"
            )
    
    async def close(self) -> None:
        """
        Close the SQLite connection.
        """
        if self.connection:
            try:
                self.connection.close()
                logger.info("SQLite connection closed")
            except Exception as e:
                logger.error(f"Error closing SQLite connection: {e}")
    
    async def _get_schema(self) -> MCPResponse:
        """
        Get the database schema.
        
        Returns:
            An MCP response with the database schema
        """
        try:
            cursor = self.connection.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get schema for each table
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}');")
                columns = [
                    {
                        "name": row[1],
                        "type": row[2],
                        "nullable": not row[3],
                        "primary_key": bool(row[5])
                    }
                    for row in cursor.fetchall()
                ]
                schema[table] = columns
            
            # Format schema as string
            schema_str = "Database Schema:\n\n"
            for table, columns in schema.items():
                schema_str += f"Table: {table}\n"
                schema_str += "-" * (len(table) + 7) + "\n"
                for column in columns:
                    pk_marker = " (PK)" if column["primary_key"] else ""
                    nullable = "" if column["nullable"] else " NOT NULL"
                    schema_str += f"  {column['name']} - {column['type']}{nullable}{pk_marker}\n"
                schema_str += "\n"
            
            return MCPResponse(
                content=schema_str,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error retrieving schema: {e}")
            return MCPResponse(
                content=None,
                success=False,
                error=f"Error retrieving schema: {str(e)}"
            ) 