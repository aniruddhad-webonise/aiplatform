"""
Interface for Model Context Protocol (MCP) servers.

This module defines the common interface that all MCP server implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """Configuration for an MCP server instance."""
    mcp_type: str
    connection_details: Dict[str, Any]
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class MCPRequest:
    """Request to an MCP server."""
    query: str
    tenant_id: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class MCPResponse:
    """Response from an MCP server."""
    content: Any
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseMCPServer(ABC):
    """Abstract base class for all MCP servers."""
    
    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP server with its configuration.
        
        Args:
            config: Configuration for this MCP server instance
        """
        self.config = config
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the MCP server connection.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def query(self, request: MCPRequest) -> MCPResponse:
        """
        Execute a query against the MCP server.
        
        Args:
            request: The request to process
            
        Returns:
            An MCP response object
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close the MCP server connection.
        """
        pass
    
    @property
    def mcp_type(self) -> str:
        """Get the type of this MCP server."""
        return self.config.mcp_type 