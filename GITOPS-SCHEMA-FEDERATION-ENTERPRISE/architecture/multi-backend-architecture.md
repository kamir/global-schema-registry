# Multi-Backend Schema Registry Architecture

**Version:** 3.0
**Date:** 2025-11-14
**Status:** Design & Implementation

---

## Executive Summary

This document defines a **flexible, pluggable architecture** for the GitOps Schema Federation Manager Enterprise Edition that abstracts away schema registry implementation details, enabling seamless integration with multiple backend types:

- Confluent Schema Registry
- Unity Catalog (Databricks)
- AWS Glue Schema Registry
- Azure Purview / Microsoft Purview
- Apicurio Registry
- Karapace
- Pulsar Schema Registry
- Redpanda Schema Registry
- Snowflake Horizon Catalog
- Google Cloud Data Catalog

---

## Architecture Principles

### 1. **Plugin-Based Architecture**
Each schema registry backend is implemented as an independent plugin conforming to a common interface.

### 2. **Abstraction Layer**
Core business logic operates on abstract schema representations, independent of backend specifics.

### 3. **Unified API**
Single REST API surface that works consistently across all backends.

### 4. **Hot-Pluggability**
Add/remove backends without redeploying the core system.

### 5. **Multi-Backend Operations**
Support queries and operations spanning multiple registries simultaneously.

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Web UI                                  │
│   ┌──────────────────────────────────────────────────────┐    │
│   │  - Registry Selector                                 │    │
│   │  - Compatibility Maintenance Dashboard               │    │
│   │  - Cross-Registry Comparison                         │    │
│   │  - Migration Wizard                                  │    │
│   └──────────────────────────────────────────────────────┘    │
└───────────────────────────┬────────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼────────────────────────────────────┐
│                    Unified API Layer                           │
│   ┌──────────────────────────────────────────────────────┐    │
│   │  - Request Router                                    │    │
│   │  - Response Normalizer                               │    │
│   │  - Multi-Backend Query Orchestrator                  │    │
│   │  - Authentication/Authorization                      │    │
│   └──────────────────────────────────────────────────────┘    │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│              Schema Registry Abstraction Layer                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │  - ISchemaRegistry (Interface)                       │    │
│   │  - ICompatibilityChecker                             │    │
│   │  - ISchemaTransformer                                │    │
│   │  - ISchemaDiscovery                                  │    │
│   │  - Plugin Registry                                   │    │
│   └──────────────────────────────────────────────────────┘    │
└────┬────────┬────────┬────────┬────────┬────────┬─────────────┘
     │        │        │        │        │        │
┌────▼───┐┌───▼───┐┌───▼───┐┌───▼───┐┌───▼───┐┌───▼───┐
│Confluent││ Unity ││  AWS  ││Apicurio││Pulsar ││Azure  │  ... more
│  SR    ││Catalog││ Glue  ││Registry││  SR   ││Purview│
│ Plugin ││Plugin ││Plugin ││ Plugin ││Plugin ││Plugin │
└────┬───┘└───┬───┘└───┬───┘└───┬───┘└───┬───┘└───┬───┘
     │        │        │        │        │        │
┌────▼────────▼────────▼────────▼────────▼────────▼────────────┐
│           Backend Schema Registry Services                    │
│  Confluent SR | Unity Catalog | AWS Glue | Apicurio | ...     │
└───────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Schema Registry Abstraction Layer

#### 1.1 ISchemaRegistry Interface

**Purpose:** Defines the contract all registry plugins must implement.

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class RegistryType(Enum):
    CONFLUENT = "confluent"
    UNITY_CATALOG = "unity_catalog"
    AWS_GLUE = "aws_glue"
    AZURE_PURVIEW = "azure_purview"
    APICURIO = "apicurio"
    KARAPACE = "karapace"
    PULSAR = "pulsar"
    REDPANDA = "redpanda"
    SNOWFLAKE = "snowflake"
    GCP_DATA_CATALOG = "gcp_data_catalog"

class SchemaFormat(Enum):
    AVRO = "avro"
    PROTOBUF = "protobuf"
    JSON_SCHEMA = "json_schema"
    ICEBERG = "iceberg"
    PARQUET = "parquet"
    OPENAPI = "openapi"
    ASYNCAPI = "asyncapi"
    SQL_DDL = "sql_ddl"

class CompatibilityMode(Enum):
    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FORWARD_FULL = "FORWARD_FULL"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"

@dataclass
class Schema:
    """Unified schema representation"""
    id: Optional[int]
    subject: str
    version: int
    schema_format: SchemaFormat
    schema_content: str  # JSON or text representation
    metadata: Dict[str, Any]
    registry_type: RegistryType
    created_at: Optional[str] = None
    created_by: Optional[str] = None

@dataclass
class CompatibilityResult:
    """Compatibility check result"""
    is_compatible: bool
    messages: List[str]
    compatibility_level: CompatibilityMode
    errors: List[str] = None

class ISchemaRegistry(ABC):
    """
    Abstract interface for all schema registry backends.
    All plugins must implement this interface.
    """

    @abstractmethod
    def get_registry_type(self) -> RegistryType:
        """Return the type of this registry"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[SchemaFormat]:
        """Return list of supported schema formats"""
        pass

    # ===== Schema CRUD Operations =====

    @abstractmethod
    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Register a new schema version

        Returns:
            Schema object with assigned ID and version
        """
        pass

    @abstractmethod
    def get_schema_by_id(self, schema_id: int) -> Schema:
        """Get schema by global ID"""
        pass

    @abstractmethod
    def get_schema_by_subject_version(
        self,
        subject: str,
        version: int
    ) -> Schema:
        """Get specific version of a schema"""
        pass

    @abstractmethod
    def get_latest_schema(self, subject: str) -> Schema:
        """Get the latest version of a schema"""
        pass

    @abstractmethod
    def list_subjects(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """
        List all subjects, optionally filtered by prefix
        """
        pass

    @abstractmethod
    def list_versions(self, subject: str) -> List[int]:
        """List all versions for a subject"""
        pass

    @abstractmethod
    def delete_schema_version(
        self,
        subject: str,
        version: int
    ) -> bool:
        """Delete a specific schema version"""
        pass

    # ===== Compatibility Operations =====

    @abstractmethod
    def check_compatibility(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        version: Optional[int] = None
    ) -> CompatibilityResult:
        """
        Check if schema is compatible with existing version(s)

        Args:
            subject: Subject name
            schema_content: Schema to check
            schema_format: Format of schema
            version: Specific version to check against (or latest if None)

        Returns:
            CompatibilityResult with detailed feedback
        """
        pass

    @abstractmethod
    def get_compatibility_mode(
        self,
        subject: Optional[str] = None
    ) -> CompatibilityMode:
        """
        Get compatibility mode (global or subject-specific)
        """
        pass

    @abstractmethod
    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """
        Set compatibility mode (global or subject-specific)
        """
        pass

    @abstractmethod
    def get_all_compatibility_modes(self) -> Dict[str, CompatibilityMode]:
        """
        Get compatibility modes for all subjects that have custom settings.

        Returns:
            Dict mapping subject name to compatibility mode
        """
        pass

    # ===== Schema Discovery =====

    @abstractmethod
    def discover_schemas(
        self,
        namespace: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Schema]:
        """
        Discover all schemas in the registry

        Args:
            namespace: Optional namespace/catalog filter
            filters: Additional filters (tags, owner, etc.)

        Returns:
            List of discovered schemas
        """
        pass

    # ===== Health & Status =====

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of the registry backend

        Returns:
            Dict with status, version, and other metadata
        """
        pass

    # ===== Metadata Operations =====

    @abstractmethod
    def get_metadata(self, subject: str, version: int) -> Dict[str, Any]:
        """Get metadata for a schema version"""
        pass

    @abstractmethod
    def update_metadata(
        self,
        subject: str,
        version: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update metadata for a schema version"""
        pass
```

#### 1.2 ICompatibilityChecker Interface

```python
class ICompatibilityChecker(ABC):
    """
    Interface for compatibility checking logic.
    Each registry may have different compatibility rules.
    """

    @abstractmethod
    def check_backward_compatibility(
        self,
        new_schema: Schema,
        old_schema: Schema
    ) -> CompatibilityResult:
        """Check backward compatibility"""
        pass

    @abstractmethod
    def check_forward_compatibility(
        self,
        new_schema: Schema,
        old_schema: Schema
    ) -> CompatibilityResult:
        """Check forward compatibility"""
        pass

    @abstractmethod
    def check_full_compatibility(
        self,
        new_schema: Schema,
        old_schema: Schema
    ) -> CompatibilityResult:
        """Check full (forward + backward) compatibility"""
        pass

    @abstractmethod
    def check_transitive_compatibility(
        self,
        new_schema: Schema,
        all_schemas: List[Schema],
        mode: CompatibilityMode
    ) -> CompatibilityResult:
        """Check transitive compatibility against all versions"""
        pass
```

#### 1.3 ISchemaTransformer Interface

```python
class ISchemaTransformer(ABC):
    """
    Interface for transforming schemas between formats.
    """

    @abstractmethod
    def can_transform(
        self,
        source_format: SchemaFormat,
        target_format: SchemaFormat
    ) -> bool:
        """Check if transformation is supported"""
        pass

    @abstractmethod
    def transform(
        self,
        schema: Schema,
        target_format: SchemaFormat,
        options: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Transform schema from one format to another

        Args:
            schema: Source schema
            target_format: Target format
            options: Transformation options (field mappings, etc.)

        Returns:
            Transformed schema
        """
        pass

    @abstractmethod
    def get_transformation_rules(
        self,
        source_format: SchemaFormat,
        target_format: SchemaFormat
    ) -> Dict[str, Any]:
        """Get default transformation rules for a format pair"""
        pass
```

---

### 2. Plugin Registry

**Purpose:** Manages registration, discovery, and lifecycle of registry plugins.

```python
from typing import Type, Dict, Optional
import importlib
import logging

class PluginRegistry:
    """
    Central registry for schema registry plugins.
    Supports dynamic plugin loading and management.
    """

    def __init__(self):
        self._plugins: Dict[RegistryType, Type[ISchemaRegistry]] = {}
        self._instances: Dict[str, ISchemaRegistry] = {}
        self.logger = logging.getLogger(__name__)

    def register_plugin(
        self,
        registry_type: RegistryType,
        plugin_class: Type[ISchemaRegistry]
    ):
        """
        Register a plugin class

        Args:
            registry_type: Type of registry this plugin handles
            plugin_class: Class implementing ISchemaRegistry
        """
        if not issubclass(plugin_class, ISchemaRegistry):
            raise ValueError(
                f"Plugin {plugin_class} must implement ISchemaRegistry"
            )

        self._plugins[registry_type] = plugin_class
        self.logger.info(f"Registered plugin for {registry_type.value}")

    def load_plugin_from_module(self, module_path: str):
        """
        Dynamically load a plugin from a Python module

        Args:
            module_path: Python import path (e.g., "plugins.confluent")
        """
        try:
            module = importlib.import_module(module_path)

            # Look for a class implementing ISchemaRegistry
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, ISchemaRegistry) and
                    attr is not ISchemaRegistry
                ):
                    instance = attr()
                    registry_type = instance.get_registry_type()
                    self.register_plugin(registry_type, attr)
                    break
        except Exception as e:
            self.logger.error(f"Failed to load plugin from {module_path}: {e}")
            raise

    def create_instance(
        self,
        registry_type: RegistryType,
        config: Dict[str, Any],
        instance_id: Optional[str] = None
    ) -> ISchemaRegistry:
        """
        Create an instance of a registry plugin

        Args:
            registry_type: Type of registry
            config: Configuration for the instance
            instance_id: Unique identifier for this instance

        Returns:
            Configured registry instance
        """
        if registry_type not in self._plugins:
            raise ValueError(
                f"No plugin registered for {registry_type.value}"
            )

        plugin_class = self._plugins[registry_type]
        instance = plugin_class(config)

        # Store instance if ID provided
        if instance_id:
            self._instances[instance_id] = instance

        return instance

    def get_instance(self, instance_id: str) -> Optional[ISchemaRegistry]:
        """Get a previously created instance by ID"""
        return self._instances.get(instance_id)

    def list_available_plugins(self) -> List[RegistryType]:
        """List all registered plugin types"""
        return list(self._plugins.keys())

    def unregister_plugin(self, registry_type: RegistryType):
        """Unregister a plugin"""
        if registry_type in self._plugins:
            del self._plugins[registry_type]
            self.logger.info(f"Unregistered plugin for {registry_type.value}")
```

---

### 3. Multi-Backend Query Orchestrator

**Purpose:** Coordinate operations across multiple registries.

```python
class MultiBackendOrchestrator:
    """
    Orchestrates operations across multiple schema registry backends.
    """

    def __init__(self, plugin_registry: PluginRegistry):
        self.plugin_registry = plugin_registry
        self.active_registries: Dict[str, ISchemaRegistry] = {}

    def add_registry(
        self,
        instance_id: str,
        registry_type: RegistryType,
        config: Dict[str, Any]
    ):
        """Add a registry backend"""
        instance = self.plugin_registry.create_instance(
            registry_type,
            config,
            instance_id
        )
        self.active_registries[instance_id] = instance

    def query_all(
        self,
        operation: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an operation across all active registries

        Args:
            operation: Method name to call on each registry
            **kwargs: Arguments to pass to the method

        Returns:
            Dict mapping instance_id to result
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                method = getattr(registry, operation)
                result = method(**kwargs)
                results[instance_id] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                results[instance_id] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def find_schema_across_registries(
        self,
        subject: str
    ) -> Dict[str, Schema]:
        """
        Find a schema by subject across all registries
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                schema = registry.get_latest_schema(subject)
                results[instance_id] = schema
            except Exception:
                # Schema not found in this registry
                pass

        return results

    def compare_compatibility_modes(self) -> Dict[str, Dict[str, CompatibilityMode]]:
        """
        Get compatibility modes from all registries for comparison
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                global_mode = registry.get_compatibility_mode()
                subject_modes = registry.get_all_compatibility_modes()

                results[instance_id] = {
                    "global": global_mode,
                    "subjects": subject_modes
                }
            except Exception as e:
                results[instance_id] = {
                    "error": str(e)
                }

        return results
```

---

## Plugin Implementation Examples

### Example 1: Confluent Schema Registry Plugin

```python
from typing import List, Optional, Dict, Any
import requests

class ConfluentSchemaRegistryPlugin(ISchemaRegistry):
    """
    Plugin for Confluent Schema Registry
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config["url"]
        self.auth = (config.get("username"), config.get("password"))
        self.session = requests.Session()
        if self.auth[0]:
            self.session.auth = self.auth

    def get_registry_type(self) -> RegistryType:
        return RegistryType.CONFLUENT

    def get_supported_formats(self) -> List[SchemaFormat]:
        return [
            SchemaFormat.AVRO,
            SchemaFormat.PROTOBUF,
            SchemaFormat.JSON_SCHEMA
        ]

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Register schema in Confluent SR"""
        url = f"{self.base_url}/subjects/{subject}/versions"

        payload = {
            "schema": schema_content,
            "schemaType": schema_format.value.upper()
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        return Schema(
            id=data["id"],
            subject=subject,
            version=data.get("version"),
            schema_format=schema_format,
            schema_content=schema_content,
            metadata=metadata or {},
            registry_type=self.get_registry_type()
        )

    def get_compatibility_mode(
        self,
        subject: Optional[str] = None
    ) -> CompatibilityMode:
        """Get compatibility mode"""
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()
        mode_str = data.get("compatibilityLevel", "BACKWARD")

        return CompatibilityMode[mode_str]

    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """Set compatibility mode"""
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        payload = {"compatibility": mode.value}

        response = self.session.put(url, json=payload)
        response.raise_for_status()

        return True

    # ... implement remaining methods ...
```

### Example 2: Unity Catalog Plugin

```python
class UnityCatalogPlugin(ISchemaRegistry):
    """
    Plugin for Databricks Unity Catalog
    """

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config["url"]
        self.token = config["token"]
        self.catalog = config.get("catalog", "main")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })

    def get_registry_type(self) -> RegistryType:
        return RegistryType.UNITY_CATALOG

    def get_supported_formats(self) -> List[SchemaFormat]:
        return [
            SchemaFormat.ICEBERG,
            SchemaFormat.AVRO,  # Via transformation
            SchemaFormat.PARQUET
        ]

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Register schema as Unity Catalog table

        Note: Unity Catalog doesn't have a "register schema" concept.
        This creates/updates a table definition.
        """
        # Parse subject as catalog.schema.table
        parts = subject.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Subject must be in format catalog.schema.table, got: {subject}"
            )

        catalog, schema_name, table_name = parts

        # Create or update table
        url = f"{self.base_url}/api/2.1/unity-catalog/tables"

        payload = {
            "name": table_name,
            "catalog_name": catalog,
            "schema_name": schema_name,
            "table_type": "MANAGED",
            "data_source_format": "ICEBERG",
            "columns": self._parse_columns(schema_content, schema_format)
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        # ... implementation continues ...

    # Unity Catalog doesn't have traditional compatibility modes
    # We implement this as best-effort schema evolution checking
    def get_compatibility_mode(
        self,
        subject: Optional[str] = None
    ) -> CompatibilityMode:
        """
        Unity Catalog uses schema evolution rules, not compatibility modes.
        Return a default.
        """
        return CompatibilityMode.BACKWARD

    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """
        Unity Catalog doesn't support setting compatibility mode directly.
        This is a no-op.
        """
        return True

    # ... implement remaining methods ...
```

---

## Configuration Management

### Registry Configuration Schema

```yaml
# config/registries.yaml

registries:
  - id: prod-confluent-us-west
    type: confluent
    enabled: true
    config:
      url: https://schema-registry.us-west-2.aws.confluent.cloud
      username: ${CONFLUENT_SR_KEY}
      password: ${CONFLUENT_SR_SECRET}
    metadata:
      region: us-west-2
      environment: production
      owner: platform-team

  - id: prod-unity-catalog
    type: unity_catalog
    enabled: true
    config:
      url: https://workspace.databricks.com
      token: ${DATABRICKS_TOKEN}
      catalog: main
    metadata:
      cloud: aws
      region: us-west-2
      environment: production

  - id: dev-aws-glue
    type: aws_glue
    enabled: true
    config:
      region: us-east-1
      aws_access_key_id: ${AWS_ACCESS_KEY_ID}
      aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}
      registry_name: dev-schemas
    metadata:
      environment: development

  - id: prod-apicurio
    type: apicurio
    enabled: true
    config:
      url: https://apicurio.company.com
      auth:
        type: oidc
        client_id: ${APICURIO_CLIENT_ID}
        client_secret: ${APICURIO_CLIENT_SECRET}
    metadata:
      environment: production
      use_case: api-schemas

  - id: staging-azure-purview
    type: azure_purview
    enabled: false  # Not yet in use
    config:
      account_name: company-purview
      tenant_id: ${AZURE_TENANT_ID}
      client_id: ${AZURE_CLIENT_ID}
      client_secret: ${AZURE_CLIENT_SECRET}
    metadata:
      environment: staging
```

---

## API Extensions

### REST API for Multi-Backend Operations

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI(title="Schema Federation API")

# ===== Registry Management =====

@app.get("/api/v1/registries")
async def list_registries():
    """List all configured registries"""
    return orchestrator.list_registries()

@app.post("/api/v1/registries/{registry_id}/test")
async def test_registry_connection(registry_id: str):
    """Test connection to a registry"""
    registry = orchestrator.get_registry(registry_id)
    return registry.health_check()

# ===== Schema Operations (Multi-Backend) =====

@app.get("/api/v1/schemas/find")
async def find_schema_across_registries(subject: str):
    """Find a schema across all registries"""
    return orchestrator.find_schema_across_registries(subject)

@app.get("/api/v1/schemas/compare")
async def compare_schemas(
    registry1_id: str,
    subject1: str,
    registry2_id: str,
    subject2: str
):
    """Compare schemas from two different registries"""
    # Implementation...

# ===== Compatibility Operations =====

@app.get("/api/v1/compatibility/overview")
async def get_compatibility_overview():
    """Get compatibility modes from all registries"""
    return orchestrator.compare_compatibility_modes()

@app.post("/api/v1/compatibility/check")
async def check_compatibility_multi_backend(
    subject: str,
    schema_content: str,
    schema_format: str,
    registry_ids: Optional[List[str]] = None
):
    """
    Check compatibility of a schema across multiple registries
    """
    results = {}

    registries = (
        [orchestrator.get_registry(rid) for rid in registry_ids]
        if registry_ids
        else orchestrator.active_registries.values()
    )

    for registry in registries:
        try:
            result = registry.check_compatibility(
                subject=subject,
                schema_content=schema_content,
                schema_format=SchemaFormat[schema_format.upper()]
            )
            results[registry.get_registry_type().value] = result
        except Exception as e:
            results[registry.get_registry_type().value] = {
                "error": str(e)
            }

    return results

@app.put("/api/v1/compatibility/{registry_id}/mode")
async def set_compatibility_mode(
    registry_id: str,
    mode: str,
    subject: Optional[str] = None
):
    """Set compatibility mode for a specific registry"""
    registry = orchestrator.get_registry(registry_id)

    try:
        compat_mode = CompatibilityMode[mode.upper()]
        success = registry.set_compatibility_mode(compat_mode, subject)

        return {
            "success": success,
            "registry_id": registry_id,
            "mode": mode,
            "subject": subject or "global"
        }
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid compatibility mode: {mode}"
        )

# ===== Bulk Operations =====

@app.post("/api/v1/bulk/set-compatibility")
async def bulk_set_compatibility(
    mode: str,
    registry_ids: Optional[List[str]] = None,
    subject_filter: Optional[str] = None
):
    """
    Set compatibility mode across multiple registries
    """
    compat_mode = CompatibilityMode[mode.upper()]
    results = {}

    registries = (
        [orchestrator.get_registry(rid) for rid in registry_ids]
        if registry_ids
        else orchestrator.active_registries.values()
    )

    for registry in registries:
        registry_id = registry.get_registry_type().value

        try:
            if subject_filter:
                # Set for filtered subjects
                subjects = registry.list_subjects(prefix=subject_filter)
                subject_results = {}

                for subject in subjects:
                    try:
                        success = registry.set_compatibility_mode(
                            compat_mode,
                            subject
                        )
                        subject_results[subject] = "success" if success else "failed"
                    except Exception as e:
                        subject_results[subject] = f"error: {str(e)}"

                results[registry_id] = subject_results
            else:
                # Set global
                success = registry.set_compatibility_mode(compat_mode)
                results[registry_id] = "success" if success else "failed"

        except Exception as e:
            results[registry_id] = f"error: {str(e)}"

    return results
```

---

## Next Steps

1. [Backend Plugin Specifications](./backend-plugin-specifications.md) - Detailed specs for each registry type
2. [Web UI Design](../ui-design/compatibility-maintenance-ui.md) - UI mockups and workflows
3. [Integration Roadmap](./integration-roadmap.md) - Phased implementation plan

---

**Version:** 3.0
**Last Updated:** 2025-11-14
**Maintained By:** Platform Engineering Team - Enterprise Division
