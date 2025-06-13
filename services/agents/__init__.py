"""
Agent implementations.

This package contains implementations of various agent types.
"""
from aiplatform.core.factories.agent_factory import AgentFactory
from aiplatform.core.interfaces.agent_interface import AgentType
from aiplatform.services.agents.chat_agent import ChatAgent
from aiplatform.services.agents.sql_agent import SQLAgent

# Register agent implementations
AgentFactory.register(AgentType.CHAT, ChatAgent)
AgentFactory.register(AgentType.SQL, SQLAgent) 