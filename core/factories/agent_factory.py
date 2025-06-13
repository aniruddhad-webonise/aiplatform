"""
Factory for creating agent instances based on configuration.
"""
from typing import Dict, Type, Any
import importlib
import logging

from ..interfaces.agent_interface import BaseAgent, AgentConfig, AgentType

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating agent instances."""
    
    # Registry of agent classes by type
    _registry: Dict[AgentType, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, agent_type: AgentType, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent class for a specific agent type.
        
        Args:
            agent_type: The type of agent
            agent_class: The class that implements the agent
        """
        cls._registry[agent_type] = agent_class
        logger.info(f"Registered agent class {agent_class.__name__} for type {agent_type.value}")
    
    @classmethod
    def create(cls, config: AgentConfig) -> BaseAgent:
        """
        Create an agent instance based on configuration.
        
        Args:
            config: Configuration for the agent
            
        Returns:
            An instance of the appropriate agent class
            
        Raises:
            ValueError: If no agent is registered for the specified type
        """
        agent_type = config.agent_type
        
        if agent_type not in cls._registry:
            raise ValueError(f"No agent registered for type: {agent_type.value}")
        
        agent_class = cls._registry[agent_type]
        logger.info(f"Creating agent of type {agent_type.value} using class {agent_class.__name__}")
        
        return agent_class(config)
    
    @classmethod
    def register_from_config(cls, config: Dict[str, Any]) -> None:
        """
        Register agent classes from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with agent registrations
        """
        for agent_config in config.get("agent_registrations", []):
            try:
                agent_type_str = agent_config["agent_type"]
                agent_type = AgentType(agent_type_str)
                
                module_path = agent_config["module_path"]
                class_name = agent_config["class_name"]
                
                module = importlib.import_module(module_path)
                agent_class = getattr(module, class_name)
                
                cls.register(agent_type, agent_class)
                
            except (KeyError, ValueError, ImportError, AttributeError) as e:
                logger.error(f"Failed to register agent from config: {e}")
                continue 