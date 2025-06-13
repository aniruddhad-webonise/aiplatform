"""
Interfaces for workflow management in the platform.

This module defines the interfaces for workflow definition, execution, and management.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class WorkflowStepType(Enum):
    """Types of workflow steps."""
    AGENT = "agent"
    CONDITION = "condition"
    TRANSFORMATION = "transformation"


@dataclass
class WorkflowStepConfig:
    """Configuration for a workflow step."""
    step_id: str
    step_type: WorkflowStepType
    agent_type: Optional[str] = None
    agent_action: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    transformation: Optional[Dict[str, Any]] = None
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """Configuration for a workflow."""
    workflow_id: str
    steps: List[WorkflowStepConfig]
    initial_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRequest:
    """Request to execute a workflow."""
    content: Any
    tenant_id: str
    request_id: str
    workflow_id: str
    initial_state: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowResponse:
    """Response from a workflow execution."""
    content: Any
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    state: Dict[str, Any] = field(default_factory=dict)


class BaseWorkflow(ABC):
    """Abstract base class for workflows."""
    
    def __init__(self, config: WorkflowConfig):
        """
        Initialize the workflow with its configuration.
        
        Args:
            config: Configuration for this workflow
        """
        self.config = config
    
    @abstractmethod
    async def execute(self, request: WorkflowRequest) -> WorkflowResponse:
        """
        Execute the workflow.
        
        Args:
            request: The request to process
            
        Returns:
            A workflow response object
        """
        pass
    
    @property
    def workflow_id(self) -> str:
        """Get the ID of this workflow."""
        return self.config.workflow_id 