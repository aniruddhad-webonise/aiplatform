"""
Core orchestrator service for the AI platform.

This module implements the central orchestration service that routes requests to appropriate
agents and manages workflows.
"""
import logging
import uuid
import re
from typing import Dict, Any, Optional, List, Tuple

from ..interfaces.agent_interface import BaseAgent, AgentConfig, AgentRequest, AgentResponse, AgentType
from ..interfaces.workflow_interface import BaseWorkflow, WorkflowRequest, WorkflowResponse
from ..factories.agent_factory import AgentFactory
from ..factories.workflow_factory import WorkflowFactory
from ..config.config_manager import ConfigManager, TenantConfig

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central orchestrator for the AI platform.
    
    The orchestrator is responsible for:
    1. Routing requests to appropriate agents or workflows
    2. Managing agent instances
    3. Executing workflows
    4. Handling multi-tenant configuration
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the orchestrator.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.agent_instances: Dict[str, Dict[str, BaseAgent]] = {}
        self.workflow_instances: Dict[str, Dict[str, BaseWorkflow]] = {}
        
        # Initialize agent and workflow instances for each tenant
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """
        Initialize agent and workflow instances for all tenants.
        """
        for tenant_id in self.config_manager.get_tenant_ids():
            tenant_config = self.config_manager.get_tenant_config(tenant_id)
            if tenant_config:
                self._initialize_tenant_components(tenant_config)
    
    def _initialize_tenant_components(self, tenant_config: TenantConfig) -> None:
        """
        Initialize agent and workflow instances for a specific tenant.
        
        Args:
            tenant_config: Configuration for the tenant
        """
        tenant_id = tenant_config.tenant_id
        
        # Initialize agent instances
        self.agent_instances[tenant_id] = {}
        for agent_id, agent_config_dict in tenant_config.agents.items():
            try:
                agent_type_str = agent_config_dict.get("type")
                if agent_type_str:
                    agent_type = AgentType(agent_type_str)
                    agent_config = AgentConfig(
                        agent_type=agent_type,
                        model_name=agent_config_dict.get("model", "gpt-4o"),
                        temperature=agent_config_dict.get("temperature", 0.0),
                        max_tokens=agent_config_dict.get("max_tokens"),
                        additional_params=agent_config_dict.get("additional_params", {})
                    )
                    agent = AgentFactory.create(agent_config)
                    self.agent_instances[tenant_id][agent_id] = agent
                    logger.info(f"Initialized agent {agent_id} for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent_id} for tenant {tenant_id}: {e}")
        
        # Initialize workflow instances
        # Note: This is a simplified implementation. In a real system, workflows
        # would be created dynamically using LangGraph based on configuration.
        self.workflow_instances[tenant_id] = {}
    
    def _determine_agent(self, query: str, tenant_config: TenantConfig) -> str:
        """
        Determine which agent should handle the request based on the query content.
        
        Args:
            query: The query string
            tenant_config: Configuration for the tenant
            
        Returns:
            The type of agent to use
        """
        # Check routing rules in order of priority
        for rule in sorted(tenant_config.routing_rules, key=lambda x: x.get("priority", 0), reverse=True):
            pattern = rule.get("pattern")
            if pattern and re.search(pattern, query, re.IGNORECASE):
                return rule["agent"]
        
        # Default to chat agent if no rules match
        return "chat"

    async def process_request(self, query: str, tenant_id: str, additional_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a request for a specific tenant."""
        try:
            # Get tenant config
            tenant_config = self.config_manager.get_tenant_config(tenant_id)
            if not tenant_config:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            # Determine which agent to use based on routing rules
            agent_type = self._determine_agent(query, tenant_config)
            
            # Get or create agent instance
            if tenant_id not in self.agent_instances:
                self.agent_instances[tenant_id] = {}
            
            if agent_type not in self.agent_instances[tenant_id]:
                # Create agent config
                agent_config = AgentConfig(
                    agent_type=AgentType(agent_type),
                    model_name=tenant_config.agents[agent_type].get("model", "gpt-4o"),
                    temperature=tenant_config.agents[agent_type].get("temperature", 0.0),
                    max_tokens=tenant_config.agents[agent_type].get("max_tokens"),
                    additional_params=tenant_config.agents[agent_type].get("additional_params", {})
                )
                
                # Create agent
                agent = AgentFactory.create(agent_config)
                self.agent_instances[tenant_id][agent_type] = agent
                logger.info(f"Created new agent instance for tenant {tenant_id}, type {agent_type}")
            
            # Get the agent instance
            agent = self.agent_instances[tenant_id][agent_type]
            
            # Create request
            request = AgentRequest(
                content=query,
                tenant_id=tenant_id,
                request_id=str(uuid.uuid4())
            )
            
            # Process request
            response = await agent.process(request)
            
            return {
                "success": response.success,
                "content": response.content,
                "error": response.error,
                "agent_type": agent_type
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _route_request(self, content: Any, tenant_config: TenantConfig) -> Tuple[str, str]:
        """
        Determine which agent or workflow should handle a request.
        
        Args:
            content: The content of the request
            tenant_config: Configuration for the tenant
            
        Returns:
            A tuple of (target_type, target_id)
        """
        # Convert content to string for pattern matching
        content_str = str(content)
        
        # Check routing rules in order
        for rule in tenant_config.routing_rules:
            pattern = rule.get("pattern")
            if pattern and re.search(pattern, content_str, re.IGNORECASE):
                if "workflow" in rule:
                    return "workflow", rule["workflow"]
                elif "agent" in rule:
                    return "agent", rule["agent"]
        
        # Default to chat agent if available
        if "chat" in tenant_config.agents:
            return "agent", "chat"
        
        # Fall back to the first available agent
        if tenant_config.agents:
            return "agent", next(iter(tenant_config.agents.keys()))
        
        # No suitable target found
        return "unknown", "unknown"
    
    async def _process_with_agent(
        self, agent: BaseAgent, content: Any, tenant_id: str, request_id: str
    ) -> AgentResponse:
        """
        Process a request with a specific agent.
        
        Args:
            agent: The agent to use
            content: The content of the request
            tenant_id: The ID of the tenant making the request
            request_id: The ID of the request
            
        Returns:
            The agent's response
        """
        request = AgentRequest(
            content=content,
            tenant_id=tenant_id,
            request_id=request_id
        )
        
        try:
            return await agent.process(request)
        except Exception as e:
            logger.error(f"Error processing request with agent: {e}")
            return AgentResponse(
                content=None,
                success=False,
                error=f"Error processing request: {str(e)}"
            ) 