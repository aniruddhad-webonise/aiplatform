"""
Base interfaces for AI agents in the platform.

This module defines the common interfaces that all agent implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass


class AgentType(Enum):
    """Enumeration of supported agent types."""
    CHAT = "chat"
    RAG = "rag"
    SQL = "sql"
    EMAIL = "email"
    PLANNER = "planner"
    # Add more agent types as needed


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    agent_type: AgentType
    model_name: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class AgentRequest:
    """Request to an agent."""
    content: Any
    tenant_id: str
    request_id: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: Any
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the agent with its configuration.
        
        Args:
            config: Configuration for this agent instance
        """
        self.config = config
    
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process a request and return a response.
        
        Args:
            request: The request to process
            
        Returns:
            An agent response object
        """
        pass
    
    @property
    def agent_type(self) -> AgentType:
        """Get the type of this agent."""
        return self.config.agent_type 