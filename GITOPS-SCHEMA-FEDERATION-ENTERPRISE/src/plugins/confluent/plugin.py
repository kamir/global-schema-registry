"""
Confluent Schema Registry plugin implementation.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...core.interfaces import ISchemaRegistry
from ...core.models import (
    CompatibilityMode,
    CompatibilityResult,
    HealthStatus,
    RegistryConfig,
    RegistryType,
    Schema,
    SchemaFormat
)


logger = logging.getLogger(__name__)


class ConfluentSchemaRegistryPlugin(ISchemaRegistry):
    """
    Plugin for Confluent Schema Registry.

    Supports:
    - AVRO, Protobuf, JSON Schema
    - All compatibility modes
    - Subject-level and global configuration
    """

    def __init__(self, config: RegistryConfig):
        """
        Initialize Confluent SR plugin.

        Args:
            config: Registry configuration
        """
        super().__init__(config)
        self.base_url = config.url.rstrip('/')

        # Create session with retry logic
        self.session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure authentication
        if config.auth.get("username") and config.auth.get("password"):
            self.session.auth = (
                config.auth["username"],
                config.auth["password"]
            )

        # Configure headers
        self.session.headers.update({
            "Content-Type": "application/vnd.schemaregistry.v1+json"
        })

        # Configure SSL
        if not config.ssl_config.get("verify", True):
            self.session.verify = False
        elif config.ssl_config.get("cert_path"):
            self.session.verify = config.ssl_config["cert_path"]

        self.timeout = config.timeout
        logger.info(f"Initialized Confluent SR plugin: {self.base_url}")

    def get_registry_type(self) -> RegistryType:
        """Return registry type."""
        return RegistryType.CONFLUENT

    def get_supported_formats(self) -> List[SchemaFormat]:
        """Return supported formats."""
        return [
            SchemaFormat.AVRO,
            SchemaFormat.PROTOBUF,
            SchemaFormat.JSON_SCHEMA
        ]

    # ===== Schema CRUD Operations =====

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Register schema in Confluent SR."""
        if schema_format not in self.get_supported_formats():
            raise ValueError(
                f"Format {schema_format.value} not supported by Confluent SR"
            )

        url = f"{self.base_url}/subjects/{subject}/versions"

        payload = {
            "schema": schema_content,
            "schemaType": self._map_format_to_confluent(schema_format)
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            return Schema(
                id=data.get("id"),
                subject=subject,
                version=data.get("version", 1),
                schema_format=schema_format,
                schema_content=schema_content,
                metadata=metadata or {},
                registry_type=self.get_registry_type()
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to register schema: {e}")
            raise

    def get_schema_by_id(self, schema_id: int) -> Schema:
        """Get schema by global ID."""
        url = f"{self.base_url}/schemas/ids/{schema_id}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            return Schema(
                id=schema_id,
                subject="unknown",  # Not provided by this endpoint
                version=0,  # Not provided by this endpoint
                schema_format=self._map_confluent_to_format(
                    data.get("schemaType", "AVRO")
                ),
                schema_content=data["schema"],
                metadata={},
                registry_type=self.get_registry_type()
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Schema ID {schema_id} not found")
            raise

    def get_schema_by_subject_version(
        self,
        subject: str,
        version: int
    ) -> Schema:
        """Get specific version of a schema."""
        url = f"{self.base_url}/subjects/{subject}/versions/{version}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            return Schema(
                id=data.get("id"),
                subject=data.get("subject", subject),
                version=data.get("version", version),
                schema_format=self._map_confluent_to_format(
                    data.get("schemaType", "AVRO")
                ),
                schema_content=data["schema"],
                metadata={},
                registry_type=self.get_registry_type()
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Subject {subject} version {version} not found")
            raise

    def get_latest_schema(self, subject: str) -> Schema:
        """Get the latest version of a schema."""
        return self.get_schema_by_subject_version(subject, "latest")

    def list_subjects(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """List all subjects."""
        url = f"{self.base_url}/subjects"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            subjects = response.json()

            if prefix:
                subjects = [s for s in subjects if s.startswith(prefix)]

            return subjects

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list subjects: {e}")
            raise

    def list_versions(self, subject: str) -> List[int]:
        """List all versions for a subject."""
        url = f"{self.base_url}/subjects/{subject}/versions"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Subject {subject} not found")
            raise

    def delete_schema_version(
        self,
        subject: str,
        version: int
    ) -> bool:
        """Delete a specific schema version."""
        url = f"{self.base_url}/subjects/{subject}/versions/{version}"

        try:
            response = self.session.delete(url, timeout=self.timeout)
            response.raise_for_status()

            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Subject {subject} version {version} not found")
            raise

    # ===== Compatibility Operations =====

    def check_compatibility(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        version: Optional[int] = None
    ) -> CompatibilityResult:
        """Check compatibility with Confluent SR."""
        version_path = f"/{version}" if version else "/latest"
        url = f"{self.base_url}/compatibility/subjects/{subject}/versions{version_path}"

        payload = {
            "schema": schema_content,
            "schemaType": self._map_format_to_confluent(schema_format)
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            return CompatibilityResult(
                is_compatible=data.get("is_compatible", False),
                messages=data.get("messages", []),
                compatibility_level=self.get_compatibility_mode(subject),
                errors=[]
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Compatibility check failed: {e}")
            return CompatibilityResult(
                is_compatible=False,
                messages=[],
                compatibility_level=CompatibilityMode.NONE,
                errors=[str(e)]
            )

    def get_compatibility_mode(
        self,
        subject: Optional[str] = None
    ) -> CompatibilityMode:
        """Get compatibility mode."""
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            mode_str = data.get("compatibilityLevel", "BACKWARD")

            return CompatibilityMode[mode_str]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Subject has no custom config, return global
                if subject:
                    return self.get_compatibility_mode()
                raise
            raise

    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """Set compatibility mode."""
        if subject:
            url = f"{self.base_url}/config/{subject}"
        else:
            url = f"{self.base_url}/config"

        payload = {"compatibility": mode.value}

        try:
            response = self.session.put(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to set compatibility mode: {e}")
            return False

    def get_all_compatibility_modes(self) -> Dict[str, CompatibilityMode]:
        """Get subject-specific compatibility overrides."""
        modes = {}

        try:
            subjects = self.list_subjects()

            for subject in subjects:
                try:
                    mode = self.get_compatibility_mode(subject)
                    modes[subject] = mode
                except:
                    # Skip subjects with no custom config
                    pass

            return modes

        except Exception as e:
            logger.error(f"Failed to get all compatibility modes: {e}")
            return {}

    # ===== Schema Discovery =====

    def discover_schemas(
        self,
        namespace: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Schema]:
        """Discover all schemas."""
        schemas = []

        try:
            subjects = self.list_subjects(prefix=namespace)

            for subject in subjects:
                try:
                    schema = self.get_latest_schema(subject)
                    schemas.append(schema)
                except Exception as e:
                    logger.warning(f"Failed to get schema for {subject}: {e}")

            return schemas

        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            return []

    # ===== Health & Status =====

    def health_check(self) -> HealthStatus:
        """Check health of Confluent SR."""
        url = f"{self.base_url}/subjects"

        start_time = time.time()
        try:
            response = self.session.get(url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000

            response.raise_for_status()

            return HealthStatus(
                healthy=True,
                status_code=response.status_code,
                message="Confluent Schema Registry is healthy",
                response_time_ms=response_time,
                metadata={
                    "url": self.base_url,
                    "registry_type": self.get_registry_type().value
                }
            )

        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000

            return HealthStatus(
                healthy=False,
                status_code=getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
                metadata={
                    "url": self.base_url,
                    "error": str(e)
                }
            )

    # ===== Metadata Operations =====

    def get_metadata(self, subject: str, version: int) -> Dict[str, Any]:
        """Get metadata for a schema version."""
        # Confluent SR doesn't have dedicated metadata endpoint
        # Return basic schema info
        schema = self.get_schema_by_subject_version(subject, version)
        return schema.metadata

    def update_metadata(
        self,
        subject: str,
        version: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update metadata for a schema version."""
        # Confluent SR doesn't support updating metadata separately
        # Would need to be stored externally
        logger.warning("Confluent SR doesn't support metadata updates natively")
        return False

    # ===== Helper Methods =====

    def _map_format_to_confluent(self, format: SchemaFormat) -> str:
        """Map SchemaFormat to Confluent schema type."""
        mapping = {
            SchemaFormat.AVRO: "AVRO",
            SchemaFormat.PROTOBUF: "PROTOBUF",
            SchemaFormat.JSON_SCHEMA: "JSON"
        }
        return mapping.get(format, "AVRO")

    def _map_confluent_to_format(self, confluent_type: str) -> SchemaFormat:
        """Map Confluent schema type to SchemaFormat."""
        mapping = {
            "AVRO": SchemaFormat.AVRO,
            "PROTOBUF": SchemaFormat.PROTOBUF,
            "JSON": SchemaFormat.JSON_SCHEMA
        }
        return mapping.get(confluent_type, SchemaFormat.AVRO)
