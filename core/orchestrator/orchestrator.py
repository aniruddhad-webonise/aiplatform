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
    
    async def process_request(self, content: Any, tenant_id: str) -> Dict[str, Any]:
        """
        Process a request from a client.
        
        Args:
            content: The content of the request
            tenant_id: The ID of the tenant making the request
            
        Returns:
            The response to the request
        """
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Get tenant configuration
        tenant_config = self.config_manager.get_tenant_config(tenant_id)
        if not tenant_config:
            return {
                "success": False,
                "error": f"Unknown tenant: {tenant_id}"
            }
        
        # Determine which agent or workflow to use
        target_type, target_id = self._route_request(content, tenant_config)
        
        if target_type == "agent":
            # Process with a single agent
            if target_id not in self.agent_instances.get(tenant_id, {}):
                return {
                    "success": False,
                    "error": f"Unknown agent: {target_id}"
                }
            
            agent = self.agent_instances[tenant_id][target_id]
            response = await self._process_with_agent(agent, content, tenant_id, request_id)
            
            return {
                "success": response.success,
                "content": response.content,
                "error": response.error,
                "metadata": response.metadata
            }
            
        elif target_type == "workflow":
            # Process with a workflow
            # Note: This is a placeholder. In a real implementation, this would
            # execute a LangGraph workflow.
            return {
                "success": True,
                "content": f"Workflow {target_id} would be executed here",
                "metadata": {
                    "workflow_id": target_id
                }
            }
            
        else:
            return {
                "success": False,
                "error": "Could not determine appropriate agent or workflow for request"
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
        content_str = str(content).lower()
        logger.info(f"Routing request: '{content_str}' for tenant: {tenant_config.tenant_id}")
        routing_config = tenant_config.routing_config or {}
        agent_rules = routing_config.get("agent_rules", {})

        # Pattern-based routing
        for rule in sorted(tenant_config.routing_rules, key=lambda x: x.get("priority", 0), reverse=True):
            pattern = rule.get("pattern")
            logger.info(f"Checking pattern rule: {pattern} for agent/workflow: {rule.get('agent') or rule.get('workflow')}")
            if pattern:
                try:
                    if re.search(pattern, content_str, re.IGNORECASE):
                        logger.info(f"Pattern matched: {pattern} -> Routing to: {rule.get('agent') or rule.get('workflow')}")
                        if "workflow" in rule:
                            return "workflow", rule["workflow"]
                        elif "agent" in rule:
                            return "agent", rule["agent"]
                except re.error as e:
                    logger.error(f"Invalid regex pattern in routing rule: {e}")
                    continue

        # Keyword-based routing
        for agent_id, agent_rule in sorted(
            agent_rules.items(),
            key=lambda x: x[1].get("fallback_priority", 0),
            reverse=True
        ):
            keywords = agent_rule.get("keywords", [])
            logger.info(f"Checking keywords for agent '{agent_id}': {keywords}")
            if any(keyword in content_str for keyword in keywords):
                logger.info(f"Keyword matched for agent '{agent_id}' -> Routing to agent.")
                if agent_id in tenant_config.agents:
                    return "agent", agent_id

        # Default to chat agent if available
        if "chat" in tenant_config.agents:
            logger.info("No pattern or keyword matched. Routing to default chat agent.")
            return "agent", "chat"

        # Fall back to the first available agent
        if tenant_config.agents:
            fallback_agent = next(iter(tenant_config.agents.keys()))
            logger.info(f"No chat agent found. Routing to first available agent: {fallback_agent}")
            return "agent", fallback_agent

        logger.error("No suitable agent or workflow found for request.")
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