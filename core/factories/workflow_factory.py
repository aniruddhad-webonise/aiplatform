"""
Factory for creating workflow instances based on configuration.
"""
from typing import Dict, Type, Any
import importlib
import logging

from ..interfaces.workflow_interface import BaseWorkflow, WorkflowConfig

logger = logging.getLogger(__name__)


class WorkflowFactory:
    """Factory for creating workflow instances."""
    
    # Registry of workflow classes by ID
    _registry: Dict[str, Type[BaseWorkflow]] = {}
    
    @classmethod
    def register(cls, workflow_id: str, workflow_class: Type[BaseWorkflow]) -> None:
        """
        Register a workflow class for a specific workflow ID.
        
        Args:
            workflow_id: The ID of the workflow
            workflow_class: The class that implements the workflow
        """
        cls._registry[workflow_id] = workflow_class
        logger.info(f"Registered workflow class {workflow_class.__name__} for ID {workflow_id}")
    
    @classmethod
    def create(cls, config: WorkflowConfig) -> BaseWorkflow:
        """
        Create a workflow instance based on configuration.
        
        Args:
            config: Configuration for the workflow
            
        Returns:
            An instance of the appropriate workflow class
            
        Raises:
            ValueError: If no workflow is registered for the specified ID
        """
        workflow_id = config.workflow_id
        
        if workflow_id not in cls._registry:
            raise ValueError(f"No workflow registered for ID: {workflow_id}")
        
        workflow_class = cls._registry[workflow_id]
        logger.info(f"Creating workflow with ID {workflow_id} using class {workflow_class.__name__}")
        
        return workflow_class(config)
    
    @classmethod
    def register_from_config(cls, config: Dict[str, Any]) -> None:
        """
        Register workflow classes from a configuration dictionary.
        
        Args:
            config: Configuration dictionary with workflow registrations
        """
        for workflow_config in config.get("workflow_registrations", []):
            try:
                workflow_id = workflow_config["workflow_id"]
                
                module_path = workflow_config["module_path"]
                class_name = workflow_config["class_name"]
                
                module = importlib.import_module(module_path)
                workflow_class = getattr(module, class_name)
                
                cls.register(workflow_id, workflow_class)
                
            except (KeyError, ImportError, AttributeError) as e:
                logger.error(f"Failed to register workflow from config: {e}")
                continue 