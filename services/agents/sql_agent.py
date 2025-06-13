"""
SQL agent implementation.

This module implements a SQL agent using LangChain and an MCP server for database access.
"""
import logging
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ...core.interfaces.agent_interface import BaseAgent, AgentConfig, AgentRequest, AgentResponse, AgentType
from ...core.interfaces.mcp_interface import MCPConfig, MCPRequest, MCPResponse
from ...core.factories.mcp_factory import MCPFactory

logger = logging.getLogger(__name__)


class SQLAgent(BaseAgent):
    """
    SQL agent for natural language database queries.
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the SQL agent.
        
        Args:
            config: Configuration for the agent
        """
        super().__init__(config)
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # Set up the default prompt template for SQL generation
        self.sql_prompt_template = ChatPromptTemplate.from_messages([
            ("system", """
            You are an expert SQL assistant. Your task is to convert natural language queries 
            into correct SQL. Return ONLY the SQL query without any explanation or comments.
            
            Database schema:
            {schema}
            """),
            ("human", "{query}")
        ])
        
        self.output_parser = StrOutputParser()
        
        # Set up the chain
        self.chain = self.sql_prompt_template | self.llm | self.output_parser
        
        # MCP server will be initialized on first use
        self.mcp_server = None
        self.mcp_config = None
        
        # Get MCP configuration from agent config
        self.mcp_params = config.additional_params.get("mcp_server", {})
    
    async def _ensure_mcp_server(self, tenant_id: str) -> None:
        """
        Ensure that the MCP server is initialized.
        
        Args:
            tenant_id: The ID of the tenant
        """
        if self.mcp_server is None:
            # Get MCP server config and schema config from additional params
            mcp_params = self.config.additional_params.get("mcp_server", {})
            schema_config = self.config.additional_params.get("schema_config", {})
            
            if not schema_config:
                raise ValueError("Schema configuration is required in SQL agent config")
            
            # Create MCP configuration
            self.mcp_config = MCPConfig(
                mcp_type=mcp_params.get("type", "sqlite"),
                connection_details=mcp_params.get("connection_details", {}),
                additional_params={"schema_config": schema_config}  # Pass schema_config as a nested parameter
            )
            
            # Create MCP server
            self.mcp_server = await MCPFactory.create(self.mcp_config)
            logger.info(f"Initialized MCP server of type {self.mcp_config.mcp_type}")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a SQL request and return a response.
        
        Args:
            request: The SQL request
            
        Returns:
            The SQL response
        """
        try:
            # Extract the input content
            query = request.content
            tenant_id = request.tenant_id
            
            # Initialize MCP server if needed
            await self._ensure_mcp_server(tenant_id)
            
            # Get schema config from additional params
            schema_config = self.config.additional_params.get("schema_config", {})
            if not schema_config:
                raise ValueError("Schema configuration is required in SQL agent config")
            
            # Build schema information from config
            schema = {}
            for table in schema_config.get("tables", []):
                schema[table] = []
                # Get column mappings for this table
                table_mappings = schema_config.get("column_mappings", {}).get(table, {})
                for natural_name, actual_name in table_mappings.items():
                    # Determine data type from data_type_rules
                    data_type = "text"  # default
                    for type_name, columns in schema_config.get("data_type_rules", {}).items():
                        if actual_name in columns:
                            data_type = type_name
                            break
                    
                    schema[table].append({
                        'column_name': actual_name,
                        'data_type': data_type,
                        'is_nullable': True
                    })
            
            # Generate SQL query from natural language
            sql_query = await self.chain.ainvoke({
                "schema": schema,
                "query": query
            })
            
            # Execute SQL query via MCP server
            mcp_request = MCPRequest(
                query=sql_query,
                tenant_id=tenant_id
            )
            mcp_response = await self.mcp_server.query(mcp_request)
            
            if not mcp_response.success:
                return AgentResponse(
                    content=None,
                    success=False,
                    error=f"SQL query execution failed: {mcp_response.error}"
                )
            
            # Format the results
            formatted_results = self._format_results(mcp_response.content, query)
            
            # Create and return the response
            return AgentResponse(
                content=formatted_results,
                success=True,
                metadata={
                    "model": self.config.model_name,
                    "agent_type": self.agent_type.value,
                    "sql_query": sql_query
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing SQL request: {e}")
            return AgentResponse(
                content=None,
                success=False,
                error=f"Error processing SQL request: {str(e)}"
            )
    
    def _format_results(self, results: Any, original_query: str) -> str:
        """
        Format SQL query results for display.
        
        Args:
            results: The query results
            original_query: The original natural language query
            
        Returns:
            Formatted results as a string
        """
        # This is a simplified implementation. In a real system, this would
        # use another LLM call to format the results in a user-friendly way.
        if isinstance(results, list) and results:
            if isinstance(results[0], dict):
                # Format as table
                columns = list(results[0].keys())
                header = " | ".join(columns)
                separator = "-" * len(header)
                rows = [" | ".join(str(row.get(col, "")) for col in columns) for row in results]
                return f"Results for: {original_query}\n\n{header}\n{separator}\n" + "\n".join(rows)
            
        # Default formatting for other result types
        return f"Results for: {original_query}\n\n{results}" 