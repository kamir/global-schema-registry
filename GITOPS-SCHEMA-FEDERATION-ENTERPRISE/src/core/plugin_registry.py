"""
Plugin registry for managing schema registry plugins.
"""

import importlib
import logging
from typing import Dict, List, Optional, Type

from .interfaces import ISchemaRegistry
from .models import RegistryConfig, RegistryType


logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for schema registry plugins.
    Supports dynamic plugin loading and management.
    """

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[RegistryType, Type[ISchemaRegistry]] = {}
        self._instances: Dict[str, ISchemaRegistry] = {}
        logger.info("Plugin registry initialized")

    def register_plugin(
        self,
        registry_type: RegistryType,
        plugin_class: Type[ISchemaRegistry]
    ):
        """
        Register a plugin class.

        Args:
            registry_type: Type of registry this plugin handles
            plugin_class: Class implementing ISchemaRegistry

        Raises:
            ValueError: If plugin_class doesn't implement ISchemaRegistry
        """
        if not issubclass(plugin_class, ISchemaRegistry):
            raise ValueError(
                f"Plugin {plugin_class} must implement ISchemaRegistry"
            )

        self._plugins[registry_type] = plugin_class
        logger.info(f"Registered plugin for {registry_type.value}")

    def load_plugin_from_module(self, module_path: str):
        """
        Dynamically load a plugin from a Python module.

        Args:
            module_path: Python import path (e.g., "plugins.confluent.plugin")

        Raises:
            ImportError: If module cannot be loaded
            ValueError: If no valid plugin found in module
        """
        try:
            module = importlib.import_module(module_path)

            # Look for a class implementing ISchemaRegistry
            plugin_found = False
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, ISchemaRegistry) and
                    attr is not ISchemaRegistry
                ):
                    instance = attr.__new__(attr)  # Create temporary instance
                    registry_type = instance.get_registry_type()
                    self.register_plugin(registry_type, attr)
                    plugin_found = True
                    break

            if not plugin_found:
                raise ValueError(
                    f"No ISchemaRegistry implementation found in {module_path}"
                )

        except Exception as e:
            logger.error(f"Failed to load plugin from {module_path}: {e}")
            raise

    def create_instance(
        self,
        config: RegistryConfig,
        instance_id: Optional[str] = None
    ) -> ISchemaRegistry:
        """
        Create an instance of a registry plugin.

        Args:
            config: Configuration for the registry
            instance_id: Unique identifier for this instance

        Returns:
            Configured registry instance

        Raises:
            ValueError: If no plugin registered for registry type
        """
        if config.type not in self._plugins:
            raise ValueError(
                f"No plugin registered for {config.type.value}. "
                f"Available: {[t.value for t in self._plugins.keys()]}"
            )

        plugin_class = self._plugins[config.type]
        instance = plugin_class(config)

        # Store instance if ID provided
        if instance_id:
            self._instances[instance_id] = instance
            logger.info(
                f"Created instance '{instance_id}' for {config.type.value}"
            )
        else:
            logger.info(f"Created anonymous instance for {config.type.value}")

        return instance

    def get_instance(self, instance_id: str) -> Optional[ISchemaRegistry]:
        """
        Get a previously created instance by ID.

        Args:
            instance_id: Instance identifier

        Returns:
            Registry instance or None if not found
        """
        return self._instances.get(instance_id)

    def list_instances(self) -> List[str]:
        """
        List all instance IDs.

        Returns:
            List of instance identifiers
        """
        return list(self._instances.keys())

    def list_available_plugins(self) -> List[RegistryType]:
        """
        List all registered plugin types.

        Returns:
            List of RegistryType enum values
        """
        return list(self._plugins.keys())

    def unregister_plugin(self, registry_type: RegistryType):
        """
        Unregister a plugin.

        Args:
            registry_type: Type of registry to unregister
        """
        if registry_type in self._plugins:
            del self._plugins[registry_type]
            logger.info(f"Unregistered plugin for {registry_type.value}")

    def remove_instance(self, instance_id: str):
        """
        Remove a registry instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id in self._instances:
            del self._instances[instance_id]
            logger.info(f"Removed instance '{instance_id}'")

    def clear_instances(self):
        """Remove all registry instances."""
        self._instances.clear()
        logger.info("Cleared all registry instances")


# Global plugin registry instance
_global_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """
    Get the global plugin registry instance.

    Returns:
        Global PluginRegistry instance
    """
    return _global_registry
