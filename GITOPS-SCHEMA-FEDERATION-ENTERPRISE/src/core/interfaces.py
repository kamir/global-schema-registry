"""
Core interfaces for schema registry plugins.
All plugins must implement these interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from .models import (
    CompatibilityMode,
    CompatibilityResult,
    HealthStatus,
    RegistryConfig,
    RegistryType,
    Schema,
    SchemaFormat
)


class ISchemaRegistry(ABC):
    """
    Abstract interface for all schema registry backends.
    All plugins must implement this interface to ensure compatibility.
    """

    def __init__(self, config: RegistryConfig):
        """
        Initialize the plugin with configuration.

        Args:
            config: Registry configuration
        """
        self.config = config

    @abstractmethod
    def get_registry_type(self) -> RegistryType:
        """
        Return the type of this registry.

        Returns:
            RegistryType enum value
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[SchemaFormat]:
        """
        Return list of supported schema formats.

        Returns:
            List of SchemaFormat enum values
        """
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
        Register a new schema version.

        Args:
            subject: Subject name (topic or table identifier)
            schema_content: Schema definition (JSON, Avro, etc.)
            schema_format: Format of the schema
            metadata: Optional metadata

        Returns:
            Schema object with assigned ID and version

        Raises:
            ValueError: If schema format is not supported
            Exception: If registration fails
        """
        pass

    @abstractmethod
    def get_schema_by_id(self, schema_id: int) -> Schema:
        """
        Get schema by global ID.

        Args:
            schema_id: Global schema ID

        Returns:
            Schema object

        Raises:
            KeyError: If schema ID not found
        """
        pass

    @abstractmethod
    def get_schema_by_subject_version(
        self,
        subject: str,
        version: int
    ) -> Schema:
        """
        Get specific version of a schema.

        Args:
            subject: Subject name
            version: Version number

        Returns:
            Schema object

        Raises:
            KeyError: If subject or version not found
        """
        pass

    @abstractmethod
    def get_latest_schema(self, subject: str) -> Schema:
        """
        Get the latest version of a schema.

        Args:
            subject: Subject name

        Returns:
            Schema object (latest version)

        Raises:
            KeyError: If subject not found
        """
        pass

    @abstractmethod
    def list_subjects(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """
        List all subjects, optionally filtered by prefix.

        Args:
            prefix: Optional prefix filter

        Returns:
            List of subject names
        """
        pass

    @abstractmethod
    def list_versions(self, subject: str) -> List[int]:
        """
        List all versions for a subject.

        Args:
            subject: Subject name

        Returns:
            List of version numbers

        Raises:
            KeyError: If subject not found
        """
        pass

    @abstractmethod
    def delete_schema_version(
        self,
        subject: str,
        version: int
    ) -> bool:
        """
        Delete a specific schema version.

        Args:
            subject: Subject name
            version: Version number

        Returns:
            True if deleted successfully

        Raises:
            KeyError: If subject or version not found
        """
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
        Check if schema is compatible with existing version(s).

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
        Get compatibility mode (global or subject-specific).

        Args:
            subject: Optional subject name (if None, returns global)

        Returns:
            CompatibilityMode enum value
        """
        pass

    @abstractmethod
    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """
        Set compatibility mode (global or subject-specific).

        Args:
            mode: Compatibility mode to set
            subject: Optional subject name (if None, sets global)

        Returns:
            True if set successfully
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
        Discover all schemas in the registry.

        Args:
            namespace: Optional namespace/catalog filter
            filters: Additional filters (tags, owner, etc.)

        Returns:
            List of discovered schemas
        """
        pass

    # ===== Health & Status =====

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Check health of the registry backend.

        Returns:
            HealthStatus with status, version, and other metadata
        """
        pass

    # ===== Metadata Operations =====

    @abstractmethod
    def get_metadata(self, subject: str, version: int) -> Dict[str, Any]:
        """
        Get metadata for a schema version.

        Args:
            subject: Subject name
            version: Version number

        Returns:
            Metadata dictionary
        """
        pass

    @abstractmethod
    def update_metadata(
        self,
        subject: str,
        version: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for a schema version.

        Args:
            subject: Subject name
            version: Version number
            metadata: New metadata

        Returns:
            True if updated successfully
        """
        pass


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
        """
        Check backward compatibility (new consumers can read old data).

        Args:
            new_schema: New schema to check
            old_schema: Old schema to check against

        Returns:
            CompatibilityResult
        """
        pass

    @abstractmethod
    def check_forward_compatibility(
        self,
        new_schema: Schema,
        old_schema: Schema
    ) -> CompatibilityResult:
        """
        Check forward compatibility (old consumers can read new data).

        Args:
            new_schema: New schema to check
            old_schema: Old schema to check against

        Returns:
            CompatibilityResult
        """
        pass

    @abstractmethod
    def check_full_compatibility(
        self,
        new_schema: Schema,
        old_schema: Schema
    ) -> CompatibilityResult:
        """
        Check full (forward + backward) compatibility.

        Args:
            new_schema: New schema to check
            old_schema: Old schema to check against

        Returns:
            CompatibilityResult
        """
        pass

    @abstractmethod
    def check_transitive_compatibility(
        self,
        new_schema: Schema,
        all_schemas: List[Schema],
        mode: CompatibilityMode
    ) -> CompatibilityResult:
        """
        Check transitive compatibility against all versions.

        Args:
            new_schema: New schema to check
            all_schemas: All previous schema versions
            mode: Compatibility mode to apply

        Returns:
            CompatibilityResult
        """
        pass


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
        """
        Check if transformation is supported.

        Args:
            source_format: Source schema format
            target_format: Target schema format

        Returns:
            True if transformation is supported
        """
        pass

    @abstractmethod
    def transform(
        self,
        schema: Schema,
        target_format: SchemaFormat,
        options: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Transform schema from one format to another.

        Args:
            schema: Source schema
            target_format: Target format
            options: Transformation options (field mappings, etc.)

        Returns:
            Transformed schema

        Raises:
            ValueError: If transformation not supported
        """
        pass

    @abstractmethod
    def get_transformation_rules(
        self,
        source_format: SchemaFormat,
        target_format: SchemaFormat
    ) -> Dict[str, Any]:
        """
        Get default transformation rules for a format pair.

        Args:
            source_format: Source schema format
            target_format: Target schema format

        Returns:
            Dictionary of transformation rules
        """
        pass
