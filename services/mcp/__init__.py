"""
MCP server implementations.

This package contains implementations of MCP servers for different data sources.
"""
from ...core.factories.mcp_factory import MCPFactory
from .sqlite_mcp import SQLiteMCPServer

# Register MCP server implementations
MCPFactory.register("sqlite", SQLiteMCPServer) 