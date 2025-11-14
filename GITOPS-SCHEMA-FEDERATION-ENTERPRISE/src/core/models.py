"""
Core data models for multi-backend schema registry system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RegistryType(Enum):
    """Supported schema registry types."""
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
    """Supported schema formats."""
    AVRO = "avro"
    PROTOBUF = "protobuf"
    JSON_SCHEMA = "json_schema"
    ICEBERG = "iceberg"
    PARQUET = "parquet"
    OPENAPI = "openapi"
    ASYNCAPI = "asyncapi"
    SQL_DDL = "sql_ddl"


class CompatibilityMode(Enum):
    """Schema compatibility modes."""
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
    """
    Unified schema representation across all registry types.
    """
    subject: str
    version: int
    schema_format: SchemaFormat
    schema_content: str
    registry_type: RegistryType
    id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "subject": self.subject,
            "version": self.version,
            "schema_format": self.schema_format.value,
            "schema_content": self.schema_content,
            "registry_type": self.registry_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by
        }


@dataclass
class CompatibilityResult:
    """
    Result of a compatibility check operation.
    """
    is_compatible: bool
    messages: List[str]
    compatibility_level: CompatibilityMode
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_compatible": self.is_compatible,
            "messages": self.messages,
            "compatibility_level": self.compatibility_level.value,
            "errors": self.errors
        }


@dataclass
class RegistryConfig:
    """
    Configuration for a schema registry instance.
    """
    id: str
    type: RegistryType
    url: str
    auth: Dict[str, Any] = field(default_factory=dict)
    ssl_config: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "url": self.url,
            "auth": self.auth,
            "ssl_config": self.ssl_config,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
            "enabled": self.enabled
        }


@dataclass
class HealthStatus:
    """
    Health status of a schema registry.
    """
    healthy: bool
    status_code: int
    message: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "healthy": self.healthy,
            "status_code": self.status_code,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata
        }


@dataclass
class BulkCheckResult:
    """
    Result of a bulk compatibility check operation.
    """
    total_checked: int
    compatible: int
    incompatible: int
    errors: int
    duration_seconds: float
    results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_checked": self.total_checked,
            "compatible": self.compatible,
            "incompatible": self.incompatible,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "results": self.results
        }
