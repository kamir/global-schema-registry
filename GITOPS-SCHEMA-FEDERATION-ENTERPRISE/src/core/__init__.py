"""
Core components for multi-backend schema registry system.
"""

from .interfaces import ISchemaRegistry, ICompatibilityChecker, ISchemaTransformer
from .models import (
    CompatibilityMode,
    CompatibilityResult,
    HealthStatus,
    RegistryConfig,
    RegistryType,
    Schema,
    SchemaFormat,
    BulkCheckResult
)
from .orchestrator import MultiBackendOrchestrator
from .plugin_registry import PluginRegistry, get_plugin_registry

__all__ = [
    # Interfaces
    "ISchemaRegistry",
    "ICompatibilityChecker",
    "ISchemaTransformer",
    # Models
    "CompatibilityMode",
    "CompatibilityResult",
    "HealthStatus",
    "RegistryConfig",
    "RegistryType",
    "Schema",
    "SchemaFormat",
    "BulkCheckResult",
    # Orchestrator
    "MultiBackendOrchestrator",
    # Plugin Registry
    "PluginRegistry",
    "get_plugin_registry",
]
