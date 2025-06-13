"""
Configuration management for the AI platform.

This module handles loading and managing configuration for the platform,
including tenant-specific settings and agent configurations.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TenantConfig:
    """Configuration for a specific tenant."""
    tenant_id: str
    name: str
    agents: Dict[str, Dict[str, Any]]
    workflows: Dict[str, Dict[str, Any]]
    routing_rules: List[Dict[str, Any]]
    routing_config: Dict[str, Any] = field(default_factory=dict)
    mcp_servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ConfigManager:
    """
    Manages configuration for the AI platform.
    
    This class handles loading and accessing configuration for:
    - Platform-wide settings
    - Tenant-specific settings
    - Agent configurations
    - Workflow configurations
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.platform_config: Dict[str, Any] = {}
        self.tenant_configs: Dict[str, TenantConfig] = {}
        
        # Load configurations
        self._load_platform_config()
        self._load_tenant_configs()
    
    def _load_platform_config(self) -> None:
        """Load platform-wide configuration."""
        config_path = os.path.join(self.config_dir, "platform.json")
        try:
            with open(config_path, "r") as f:
                self.platform_config = json.load(f)
            logger.info(f"Loaded platform configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load platform configuration: {e}")
            self.platform_config = {}
    
    def _load_tenant_configs(self) -> None:
        """Load configurations for all tenants."""
        tenants_dir = os.path.join(self.config_dir, "tenants")
        try:
            for filename in os.listdir(tenants_dir):
                if filename.endswith(".json"):
                    tenant_id = filename[:-5]  # Remove .json extension
                    config_path = os.path.join(tenants_dir, filename)
                    with open(config_path, "r") as f:
                        config_data = json.load(f)
                        self.tenant_configs[tenant_id] = TenantConfig(
                            tenant_id=config_data["tenant_id"],
                            name=config_data["name"],
                            agents=config_data.get("agents", {}),
                            workflows=config_data.get("workflows", {}),
                            routing_rules=config_data.get("routing_rules", []),
                            routing_config=config_data.get("routing_config", {}),
                            mcp_servers=config_data.get("mcp_servers", {})
                        )
                    logger.info(f"Loaded configuration for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to load tenant configurations: {e}")
    
    def get_platform_config(self) -> Dict[str, Any]:
        """
        Get platform-wide configuration.
        
        Returns:
            Platform configuration dictionary
        """
        return self.platform_config
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """
        Get configuration for a specific tenant.
        
        Args:
            tenant_id: ID of the tenant
            
        Returns:
            Tenant configuration or None if not found
        """
        return self.tenant_configs.get(tenant_id)
    
    def get_tenant_ids(self) -> List[str]:
        """
        Get list of all tenant IDs.
        
        Returns:
            List of tenant IDs
        """
        return list(self.tenant_configs.keys())
    
    def _resolve_path(self, relative_path: str) -> str:
        """
        Resolve a path relative to the configuration directory.
        
        Args:
            relative_path: Path relative to the configuration directory
            
        Returns:
            Absolute path
        """
        if os.path.isabs(self.config_dir):
            return os.path.join(self.config_dir, relative_path)
        else:
            # Resolve relative to the current working directory
            return os.path.join(os.getcwd(), self.config_dir, relative_path) 