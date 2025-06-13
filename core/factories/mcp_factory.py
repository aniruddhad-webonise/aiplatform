"""
Factory for creating MCP server instances based on configuration.
"""
from typing import Dict, Type, Any
import importlib
import logging

from ..interfaces.mcp_interface import BaseMCPServer, MCPConfig

logger = logging.getLogger(__name__)


class MCPFactory:
    """Factory for creating MCP server instances."""
    
    # Registry of MCP server classes by type
    _registry: Dict[str, Type[BaseMCPServer]] = {}
    
    @classmethod
    def register(cls, mcp_type: str, mcp_class: Type[BaseMCPServer]) -> None:
        """
        Register an MCP server class for a specific MCP type.
        
        Args:
            mcp_type: The type of MCP server
            mcp_class: The class that implements the MCP server
        """
        cls._registry[mcp_type] = mcp_class
        logger.info(f"Registered MCP server class {mcp_class.__name__} for type {mcp_type}")
    
    @classmethod
    async def create(cls, config: MCPConfig) -> BaseMCPServer:
        """
        Create an MCP server instance based on configuration.
        
        Args:
            config: Configuration for the MCP server
            
        Returns:
            An instance of the appropriate MCP server class
            
        Raises:
            ValueError: If no MCP server is registered for the specified type
        """
        mcp_type = config.mcp_type
        
        if mcp_type not in cls._registry:
            raise ValueError(f"No MCP server registered for type: {mcp_type}")
        
        mcp_class = cls._registry[mcp_type]
        logger.info(f"Creating MCP server of type {mcp_type} using class {mcp_class.__name__}")
        
        mcp_server = mcp_class(config)
        
        # Initialize the MCP server
        success = await mcp_server.initialize()
        if not success:
            raise RuntimeError(f"Failed to initialize MCP server of type {mcp_type}")
        
        return mcp_server
    
    @classmethod
    def register_from_config(cls, config: Dict[str, Any]) -> None:
        """
        Register MCP server classes from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with MCP server registrations
        """
        for mcp_config in config.get("mcp_registrations", []):
            try:
                mcp_type = mcp_config["mcp_type"]
                
                module_path = mcp_config["module_path"]
                class_name = mcp_config["class_name"]
                
                module = importlib.import_module(module_path)
                mcp_class = getattr(module, class_name)
                
                cls.register(mcp_type, mcp_class)
                
            except (KeyError, ImportError, AttributeError) as e:
                logger.error(f"Failed to register MCP server from config: {e}")
                continue 